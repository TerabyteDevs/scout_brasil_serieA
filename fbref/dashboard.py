

import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Scout Brasileirão")

# --- CARREGAMENTO E PREPARAÇÃO DOS DADOS ---
@st.cache_data
def load_data(file_path):
    """Carrega e prepara os dados do arquivo Excel."""
    try:
        df = pd.read_excel(file_path)
        # --- LÓGICA DA IDADE ---
        # Converte a coluna de data de nascimento para o formato datetime
        df['birth_date_dt'] = pd.to_datetime(df['birth_date'], format='%d/%m/%Y', errors='coerce')
        # Calcula a idade atual do jogador
        today = datetime.now()
        df['age'] = df['birth_date_dt'].apply(
            lambda birth_date: today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if pd.notna(birth_date) else None
        )
        return df
    except FileNotFoundError:
        return None

# Nome do arquivo que você gerou com os dados do Brasileirão
DATA_FILE = "fbref_player_stats_final.xlsx"

df = load_data(DATA_FILE)

if df is None:
    st.error(f"ARQUIVO NÃO ENCONTRADO: '{DATA_FILE}'. Verifique se o arquivo está na mesma pasta que o dashboard.py.")
    st.stop()

# --- BARRA LATERAL COM FILTROS ---
st.sidebar.header("Filtros de Scout")

# Filtro por Posição
pos_input = st.sidebar.text_input("Buscar Posição (ex: FW, MF, DF, GK)", "").upper()

# Filtro por Idade (agora usando a idade calculada)
min_age, max_age = int(df['age'].min()), int(df['age'].max())
selected_age = st.sidebar.slider(
    "Faixa de Idade",
    min_value=min_age,
    max_value=max_age,
    value=(min_age, max_age) # value é uma tupla com (min, max)
)

# Filtro por Gols Marcados
# O nome da coluna "StandardStats_Gls" veio da sua pipeline
goals_col = 'StandardStats_Gls'
if goals_col in df.columns:
    min_goals, max_goals = int(df[goals_col].min()), int(df[goals_col].max())
    selected_goals = st.sidebar.slider(
        "Mínimo de Gols Marcados",
        min_value=min_goals,
        max_value=max_goals,
        value=min_goals
    )
else:
    selected_goals = 0

# --- LÓGICA DE FILTRAGEM ---
# Filtra o DataFrame com base nas seleções do usuário
df_filtered = df[
    (df['age'].between(selected_age[0], selected_age[1]))
]

if pos_input:
    df_filtered = df_filtered[df_filtered['position'].str.contains(pos_input, na=False)]

if selected_goals > 0 and goals_col in df_filtered.columns:
    df_filtered = df_filtered[df_filtered[goals_col] >= selected_goals]

# --- PÁGINA PRINCIPAL ---
st.title("⚽ Dashboard de Scout - Brasileirão")
st.markdown("Use os filtros na barra à esquerda para encontrar os jogadores que você procura.")

st.header("Resultados da Busca")
st.markdown(f"**{len(df_filtered)} jogadores encontrados**")

# Remove colunas técnicas antes de exibir
columns_to_show = [col for col in df_filtered.columns if col not in ['birth_date_dt', 'age_standardized']]

st.dataframe(df_filtered[columns_to_show])