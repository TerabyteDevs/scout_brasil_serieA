# fbref/pipelines.py
import pandas as pd
import re
from datetime import datetime

class ExcelExportPipeline:
    def __init__(self):
        self.items_by_spider = {}

    def open_spider(self, spider):
        # Cria uma lista de itens específica para cada spider que for aberta
        self.items_by_spider[spider.name] = []

    def process_item(self, item, spider):
        # Adiciona o item na lista correta da spider em execução
        self.items_by_spider[spider.name].append(dict(item))
        return item

    def close_spider(self, spider):
        # --- LÓGICA INTELIGENTE ---
        # SÓ executa o código de Excel para as spiders de dados de jogadores
        spiders_for_excel = ['fbref_stats', 'leagues_from_json'] # Adicione aqui outras spiders de stats se criar
        
        if spider.name not in spiders_for_excel:
            spider.logger.info(f"Spider '{spider.name}' não está configurada para exportar Excel. Pulando pipeline.")
            return # Para a execução da pipeline aqui para spiders como a 'league_links'

        # Pega a lista de itens da spider que acabou de fechar
        items = self.items_by_spider[spider.name]

        if not items:
            spider.logger.warning("Nenhum item foi coletado para salvar.")
            return
            
        df = pd.DataFrame(items)
        spider.logger.info(f"DataFrame inicial criado com {len(df)} linhas. Iniciando tratamento...")

        # O restante do seu código de tratamento continua aqui...
        # ... (todo o seu código de pivotagem, cálculo de idade, etc.) ...
        
        # --- ETAPA 8: SALVAR O ARQUIVO FINAL ---
        output_filename = f"fbref_{spider.name}_final.xlsx"
        # final_df.to_excel(output_filename, index=False) # Certifique-se de que sua variável final se chama final_df
        # spider.logger.info(f"Arquivo Excel final e organizado '{output_filename}' salvo com sucesso.")
        
        # Nota: Colei seu código de tratamento abaixo para garantir que nada se perca.
        # Você pode substituir da linha 70 em diante pelo seu código completo se preferir.
        
        # Pré-processamento da coluna 'age' para ser usada na chave de unificação
        if 'age' in df.columns:
            df['age_standardized'] = df['age'].astype(str).str.split('-').str[0]

        # --- ETAPA 1: UNIFICAÇÃO DOS DADOS DO JOGADOR ---
        id_cols = ['player', 'nationality', 'position', 'team', 'age', 'birth_year']
        essential_keys = ['player', 'nationality', 'age_standardized']
        if not all(key in df.columns for key in essential_keys):
            spider.logger.error(f"Colunas essenciais para a chave única ({', '.join(essential_keys)}) não foram encontradas.")
            df.to_excel("fbref_player_stats_raw_error.xlsx", index=False)
            return

        df['player_id'] = (df['player'].fillna('') + '_' + 
                           df['nationality'].fillna('') + '_' + 
                           df['age_standardized'].astype(str).fillna(''))

        demographic_cols = [col for col in id_cols if col in df.columns]
        demographics_df = df[['player_id'] + demographic_cols].copy()
        consolidated_demographics = demographics_df.groupby('player_id').first().reset_index()
        
        # --- ETAPA 2: PIVOTAGEM DAS ESTATÍSTICAS ---
        pivot_col = 'category'
        value_cols = [col for col in df.columns if col not in demographic_cols and col not in ['category', 'player_id', 'age_standardized']]
        stats_pivot_df = pd.pivot_table(df, index='player_id', columns=pivot_col, values=value_cols, aggfunc='first')
        new_columns = []
        for col_stat, col_cat in stats_pivot_df.columns:
            cat_cleaned = re.sub(r'[^A-Za-z0-9]+', '', col_cat)
            new_columns.append(f"{cat_cleaned}_{col_stat}")
        stats_pivot_df.columns = new_columns
        stats_pivot_df.reset_index(inplace=True)
        
        # --- ETAPA 3: JUNÇÃO DOS DADOS ---
        final_df = pd.merge(consolidated_demographics, stats_pivot_df, on='player_id', how='left')
        final_df.drop('player_id', axis=1, inplace=True)

        # --- ETAPA 4: CÁLCULO DA DATA DE NASCIMENTO ---
        reference_date = pd.to_datetime(datetime.now().date())
        final_df['birth_date'] = pd.NaT
        valid_rows_mask = final_df['age'].str.contains('-', na=False)

        if valid_rows_mask.any():
            valid_data = final_df[valid_rows_mask].copy()
            age_parts = valid_data['age'].str.split('-', n=1, expand=True)
            valid_data['age_years'] = pd.to_numeric(age_parts[0], errors='coerce')
            valid_data['age_days'] = pd.to_numeric(age_parts[1], errors='coerce').fillna(0)
            birth_dates = valid_data.apply(
                lambda row: reference_date - pd.DateOffset(years=row['age_years']) - pd.to_timedelta(row['age_days'], unit='d'),
                axis=1
            )
            final_df.loc[valid_rows_mask, 'birth_date'] = birth_dates
        
        final_df['birth_date'] = final_df['birth_date'].dt.strftime('%d/%m/%Y').fillna('')
        final_df.drop(['age', 'birth_year'], axis=1, inplace=True, errors='ignore')

        # --- ETAPA 5: TRATAMENTO DOS TIPOS DE DADOS ---
        id_cols_final = ['player', 'birth_date', 'nationality', 'position', 'team']
        stat_cols_to_convert = [col for col in final_df.columns if col not in id_cols_final]
        for col in stat_cols_to_convert:
            final_df[col] = pd.to_numeric(final_df[col], errors='coerce')
        
        # --- ETAPA 6: PREENCHER CÉLULAS VAZIAS ---
        text_cols = ['player', 'birth_date', 'nationality', 'position', 'team']
        numeric_cols_to_fill = [col for col in final_df.columns if col not in text_cols]
        final_df[numeric_cols_to_fill] = final_df[numeric_cols_to_fill].fillna(0)

        # --- ETAPA 7: REORDENAÇÃO DAS COLUNAS ---
        category_order = ["Standard Stats", "Goalkeeping", "Advanced Goalkeeping", "Shooting", "Passing", "Pass Types", "Goal and Shot Creation", "Defensive Actions", "Possession", "Playing Time", "Miscellaneous Stats"]
        cleaned_category_order = [re.sub(r'[^A-Za-z0-9]+', '', cat) for cat in category_order]

        final_ordered_columns = [col for col in id_cols_final if col in final_df.columns]
        for category_name in cleaned_category_order:
            cols_for_this_category = sorted([col for col in final_df.columns if col.startswith(f"{category_name}_")])
            final_ordered_columns.extend(cols_for_this_category)
        remaining_cols = sorted([col for col in final_df.columns if col not in final_ordered_columns])
        final_ordered_columns.extend(remaining_cols)
        
        final_df = final_df[final_ordered_columns]
        
        # --- ETAPA 8: SALVAR O ARQUIVO FINAL ---
        output_filename = f"fbref_{spider.name}_final.xlsx"
        final_df.to_excel(output_filename, index=False)
        spider.logger.info(f"Arquivo Excel final e organizado '{output_filename}' salvo com sucesso.")