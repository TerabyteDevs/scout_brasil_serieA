# app.py
import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io
import math
import os
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(
    page_title="Scout Platform",
    page_icon="⚽",
    layout="wide"
)

# --- Funções de Caching e Processamento de Dados ---

@st.cache_data
def load_data(file_path):
    """Carrega, limpa e pré-calcula os dados dos jogadores a partir do arquivo Excel."""
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        st.error(f"Não foi possível carregar o arquivo Excel '{file_path}'. Erro: {e}")
        return pd.DataFrame()

    df.columns = [col.strip() for col in df.columns]
    df['birth_date'] = pd.to_datetime(df['birth_date'], format='%d/%m/%Y', errors='coerce')
    df['age'] = (datetime.now() - df['birth_date']).dt.days / 365.25
    df = df[df['age'].notna()]
    df['age'] = df['age'].astype(int)
    
    position_map = {
        'Goalkeeper': 'Goleiro',
        'Defender': 'Defensor', 'Fullback': 'Defensor', 'Left Back': 'Defensor', 'Right Back': 'Defensor', 'Center Back': 'Defensor',
        'Midfielder': 'Meio-campista', 'Defensive Midfielder': 'Meio-campista', 'Central Midfielder': 'Meio-campista', 'Left Midfielder': 'Meio-campista', 'Right Midfielder': 'Meio-campista', 'Wide Midfielder': 'Meio-campista', 'Attacking Midfielder': 'Meio-campista',
        'Forward': 'Atacante', 'Left Winger': 'Atacante', 'Right Winger': 'Atacante'
    }
    df['general_position'] = df['position'].str.split(',').str[0].str.strip().map(position_map).fillna('Outro')

    return df

@st.cache_data
def load_descriptions(file_path):
    """Carrega as descrições das colunas a partir do arquivo CSV."""
    try:
        desc_df = pd.read_csv(file_path, delimiter=';')
        descriptions = pd.Series(desc_df.iloc[:, 2].values, index=desc_df.iloc[:, 0]).to_dict()
        return descriptions
    except Exception:
        st.warning(f"Arquivo de descrições '{file_path}' não encontrado. As dicas de ajuda não serão exibidas.")
        return {}

def get_data_update_date(file_path):
    """Pega a data da última modificação do arquivo de dados."""
    try:
        mod_time = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y')
    except FileNotFoundError:
        return "Data não disponível"

# --- Seção 1: Plataforma de Scout ---
def render_scout_page(df, descriptions):
    """Renderiza a página de busca e filtragem de jogadores."""
    
    title_cols = st.columns([0.9, 0.1])
    title_cols[0].title("Plataforma Avançada de Scout ⚽")
    with title_cols[1]:
        st.write("") 
        with st.popover("❔ Sobre", use_container_width=True):
            st.markdown("""
            ### Sobre a Plataforma de Scout
            Esta é uma ferramenta interativa para análise e descoberta de jogadores de futebol, utilizando dados estatísticos detalhados.
            #### Como Usar:
            1.  **Filtros Gerais:** Use os filtros de identificação (idade, posição, etc.).
            2.  **Filtros Específicos:** Abra as seções de estatísticas e ajuste os sliders para definir valores mínimos.
            3.  **Dicas:** Passe o mouse sobre qualquer slider para ver a descrição do atributo.
            4.  **Pesquisar:** Após configurar os filtros, clique em **"Executar Pesquisa"**.
            5.  **Analisar:** Navegue pelos resultados e clique em um jogador para expandir sua ficha detalhada.
            """)

    data_update_date = get_data_update_date('fbref_player_stats_final.xlsx')
    st.caption(f"📅 Dados atualizados em: **{data_update_date}**")
    st.markdown("Use os filtros abaixo para encontrar jogadores que correspondam aos seus critérios de busca.")

    if 'scout_results' not in st.session_state: st.session_state.scout_results = pd.DataFrame()
    if 'scout_page_number' not in st.session_state: st.session_state.scout_page_number = 0

    CATEGORIES = {
        "ADVANCED GOALKEEPING": "Advanced_Goalkeeping", "GOALKEEPING": "Goalkeeping",
        "DEFENSIVE ACTIONS": "Defensive_Actions", "GOAL AND SHOT CREATION": "Goal_and_Shot_Creation",
        "MISCELLANEOUS": "Miscellaneous_Stats", "PASSING": "Passing", "PASS TYPES": "Pass_Types",
        "PLAYING TIME": "Playing_Time", "POSSESSION": "Possession", "SHOOTING": "Shooting"
    }
    
    if not df.empty:
        with st.form(key='filter_form'):
            with st.expander("🔎 DADOS DE IDENTIFICAÇÃO", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                age_val = c1.slider('Idade', int(df['age'].min()), int(df['age'].max()), (int(df['age'].min()), int(df['age'].max())))
                nat_val = c2.multiselect('Nacionalidade', options=sorted(df['nationality'].dropna().str.split(',').explode().str.strip().unique()))
                pos_val = c3.multiselect('Posição', options=sorted(df['position'].dropna().str.split(',').explode().str.strip().unique()))
                team_val = c4.multiselect('Clube', options=sorted(df['team'].dropna().unique()))

            for cat_name, cat_prefix in CATEGORIES.items():
                relevant_cols = [col for col in df.columns if col.startswith(cat_prefix) and pd.api.types.is_numeric_dtype(df[col])]
                if relevant_cols:
                    with st.expander(f"📊 {cat_name}"):
                        for col_name in relevant_cols:
                            help_text = descriptions.get(col_name, "Descrição não disponível.")
                            max_val = float(df[col_name].max())
                            st.slider(label=col_name.replace(cat_prefix + '_', '').replace('_', ' ').title(),
                                      min_value=0.0, max_value=max_val, value=0.0,
                                      help=help_text, key=col_name)
            search_button = st.form_submit_button(label='Executar Pesquisa', use_container_width=True, type="primary")
        
        if search_button:
            filtered_df = df.copy()
            filtered_df = filtered_df[filtered_df['age'].between(age_val[0], age_val[1])]
            if nat_val: filtered_df = filtered_df[filtered_df['nationality'].str.contains('|'.join(re.escape(n) for n in nat_val), na=False)]
            if pos_val: filtered_df = filtered_df[filtered_df['position'].str.contains('|'.join(re.escape(p) for p in pos_val), na=False)]
            if team_val: filtered_df = filtered_df[filtered_df['team'].isin(team_val)]
            for key, value in st.session_state.items():
                if key in df.columns and value > 0:
                    filtered_df = filtered_df[filtered_df[key] >= value]
            st.session_state.scout_results = filtered_df
            st.session_state.scout_page_number = 0
        
        results_df = st.session_state.scout_results
        ITEMS_PER_PAGE = 10
        if not results_df.empty:
            st.success(f"Encontrados {len(results_df)} jogadores.")
            total_pages = math.ceil(len(results_df) / ITEMS_PER_PAGE)
            start_idx = st.session_state.scout_page_number * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            paginated_results = results_df.iloc[start_idx:end_idx]
            results_container = st.container(border=True)
            for _, player in paginated_results.iterrows():
                with results_container:
                    st.subheader(f"👤 {player['player']}")
                    st.caption(f"**{player['age']} anos** | {player['position']} | {player['nationality']} | **Clube:** {player['team']}")
                    with st.expander("Visualizar ficha completa"):
                        for cat_name, cat_prefix in CATEGORIES.items():
                            player_stats = player.filter(like=cat_prefix)
                            player_stats = player_stats[player_stats > 0]
                            if not player_stats.empty:
                                with st.container(border=True):
                                    st.subheader(cat_name.title())
                                    cols = st.columns(4)
                                    col_idx = 0
                                    for stat, value in player_stats.items():
                                        stat_name = stat.replace(cat_prefix + '_', '').replace('_', ' ').title()
                                        cols[col_idx].metric(label=stat_name, value=f"{value:.2f}" if isinstance(value, float) else value)
                                        col_idx = (col_idx + 1) % 4
                    st.divider()
            st.write("")
            nav_cols = st.columns([1, 2, 1])
            with nav_cols[0]:
                if st.button('⬅️ Anterior', use_container_width=True, disabled=(st.session_state.scout_page_number < 1)):
                    st.session_state.scout_page_number -= 1
                    st.rerun()
            with nav_cols[1]:
                st.markdown(f"<p style='text-align: center; font-weight: bold;'>Página {st.session_state.scout_page_number + 1} de {total_pages}</p>", unsafe_allow_html=True)
            with nav_cols[2]:
                if st.button('Próxima ➡️', use_container_width=True, disabled=(st.session_state.scout_page_number >= total_pages - 1)):
                    st.session_state.scout_page_number += 1
                    st.rerun()
        elif search_button:
            st.warning("Nenhum jogador encontrado com os filtros selecionados.")
        st.divider()
        action_cols = st.columns(2)
        if action_cols[0].button('Limpar Filtros e Busca', use_container_width=True):
            st.session_state.scout_results = pd.DataFrame()
            st.session_state.scout_page_number = 0
            st.rerun()
        if not results_df.empty:
            csv = results_df.to_csv(index=False).encode('utf-8')
            action_cols[1].download_button(label="Baixar Resultados (CSV)", data=csv,
                                           file_name=f"scout_results_{datetime.now().strftime('%Y%m%d')}.csv",
                                           mime='text/csv', use_container_width=True)
        st.write("")
        _, popover_col = st.columns([0.8, 0.2])
        with popover_col:
            with st.popover("🚀 Melhorias Futuras", use_container_width=True):
                st.markdown("""
                ### Evolução da Plataforma
                - **Enriquecimento dos Dados:** Integrar novas fontes para incluir Valor de Mercado, Características, Pontos Fortes e Fracos.
                - **Expansão da Cobertura:** Adicionar a coleta de dados de outras grandes ligas ao redor do mundo.
                """)

# --- Seção 2: Rankings ---
def render_rankings_page(df):
    """Renderiza a página com rankings de jogadores por atributo."""
    
    title_cols = st.columns([0.9, 0.1])
    title_cols[0].title("Rankings da Liga 🏆")
    with title_cols[1]:
        st.write("")
        with st.popover("❔ Sobre", use_container_width=True):
            st.markdown("""
            ### Sobre a Seção de Rankings
            Esta área permite visualizar os melhores jogadores da liga em estatísticas específicas.
            **Como Usar:**
            1.  **Escolha o Atributo:** Selecione a estatística que você deseja analisar.
            2.  **Defina o Top:** Escolha quantos jogadores quer ver no ranking (Top 5, 10, etc.).
            3.  **Filtre por Minutos:** Ajuste o mínimo de minutos jogados para uma comparação mais justa.
            4.  **Analise o Contexto:** Abaixo do gráfico, veja as métricas gerais do atributo, separadas por posição.
            """)
    st.markdown("Selecione um atributo para ver os líderes e comparar com as médias da posição.")

    if df.empty:
        st.warning("Não há dados para exibir. Verifique o arquivo de dados.")
        return

    # Seletores para o ranking
    numeric_cols = sorted([col for col in df.select_dtypes(include='number').columns if col not in ['age', 'minutes_90s']])
    
    col1, col2, col3 = st.columns(3) # Colunas para os 3 filtros
    selected_stat = col1.selectbox("Selecione um atributo para o ranking:", numeric_cols, index=numeric_cols.index("Shooting_goals") if "Shooting_goals" in numeric_cols else 0)
    top_n = col2.selectbox("Top N:", [5, 10, 15, 20], index=1)
    # Novo filtro de minutos mínimos jogados
    min_minutes_played = col3.number_input("Mínimo de minutos jogados:", min_value=0, value=90, step=90, help="Filtra jogadores com um mínimo de tempo em campo.")

    if selected_stat:
        st.subheader(f"Top {top_n} jogadores em {selected_stat.replace('_', ' ').title()}")
        
        # Aplica o filtro de minutos mínimos
        df_filtered_for_ranking = df[df['Playing_Time_minutes'] >= min_minutes_played] if 'Playing_Time_minutes' in df.columns else df
        
        top_players = df_filtered_for_ranking.nlargest(top_n, selected_stat)
        
        if top_players.empty:
            st.warning(f"Nenhum jogador encontrado com mais de {min_minutes_played} minutos jogados para esta estatística.")
        else:
            fig = px.bar(top_players, x=selected_stat, y='player', orientation='h', text=selected_stat,
                         hover_data=['team', 'age', 'position'])
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Métricas por Posição (Referente ao Atributo Selecionado)")
        position_stats = df_filtered_for_ranking.groupby('general_position')[selected_stat].describe().round(2)
        pos_cols = st.columns(len(position_stats))
        for i, (pos, stats) in enumerate(position_stats.iterrows()):
            with pos_cols[i]:
                st.markdown(f"#### {pos}")
                st.metric(label="Média", value=stats['mean'])
                st.metric(label="Máximo", value=stats['max'])
                st.metric(label="Mínimo", value=stats['min'])
                st.metric(label="Mediana (50%)", value=stats['50%'])
                st.caption(f"Baseado em {int(stats['count'])} jogadores.")

    st.write("")
    st.divider()
    _, popover_col = st.columns([0.8, 0.2])
    with popover_col:
        with st.popover("🚀 Melhorias Futuras", use_container_width=True):
            st.markdown("""
            ### Evolução da Plataforma
            - **Enriquecimento dos Dados:** Integrar novas fontes para incluir Valor de Mercado, Características, Pontos Fortes e Fracos.
            - **Expansão da Cobertura:** Adicionar a coleta de dados de outras grandes ligas ao redor do mundo.
            """)

# --- Lógica Principal (Router) ---
st.sidebar.title("Navegação")
page_options = ["Plataforma de Scout", "Rankings"]
page_selection = st.sidebar.radio("Escolha uma seção:", page_options)

df_main = load_data('fbref_player_stats_final.xlsx')
descriptions_main = load_descriptions('descrição.csv')

if page_selection == "Plataforma de Scout":
    render_scout_page(df_main, descriptions_main)
elif page_selection == "Rankings":
    render_rankings_page(df_main)