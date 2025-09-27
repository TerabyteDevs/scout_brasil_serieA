# fbref/pipelines.py
import pandas as pd
import re
import json
from datetime import datetime

class ExcelExportPipeline:
    def __init__(self):
        self.items = []

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        if not self.items:
            spider.logger.warning("Nenhum item foi coletado para salvar.")
            return
            
        df = pd.DataFrame(self.items)
        spider.logger.info(f"DataFrame inicial criado com {len(df)} linhas. Iniciando tratamento...")

        if 'age' in df.columns:
            df['age_standardized'] = df['age'].astype(str).str.split('-').str[0]

        # --- ETAPA 1: UNIFICAÇÃO DOS DADOS DO JOGADOR ---
        id_cols = ['player', 'nationality', 'position', 'team', 'age', 'birth_year']
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
        for stat, category in stats_pivot_df.columns:
            category_cleaned = category.replace(' ', '_')
            new_columns.append(f"{category_cleaned}_{stat}")
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
                axis=1)
            final_df.loc[valid_rows_mask, 'birth_date'] = birth_dates
        final_df['birth_date'] = final_df['birth_date'].dt.strftime('%d/%m/%Y').fillna('')
        final_df.drop(['age', 'birth_year', 'age_standardized'], axis=1, inplace=True, errors='ignore')

        # --- ETAPA 5: EXPANSÃO DAS ABREVIAÇÕES ---
        spider.logger.info("Expandindo abreviações das colunas 'nationality' e 'position'...")

        # Carrega mapeamentos de arquivos JSON
        try:
            with open('nationalities.json', 'r', encoding='utf-8') as f:
                nationality_map = {k.lower(): v for k, v in json.load(f).items()}
        except FileNotFoundError:
            spider.logger.error("Arquivo 'nationalities.json' não encontrado!")
            nationality_map = {}
        
        try:
            with open('positions.json', 'r', encoding='utf-8') as f:
                position_map = {k.upper(): v for k, v in json.load(f).items()}
        except FileNotFoundError:
            spider.logger.error("Arquivo 'positions.json' não encontrado!")
            position_map = {}

        # Função genérica para expandir abreviações
        def expand_abbreviations(value, mapping, case='lower'):
            if not isinstance(value, str):
                return value
            parts = [p.strip() for p in value.split(',')]
            
            if case == 'upper':
                expanded_parts = [mapping.get(p.upper(), p) for p in parts]
            else: # default to lower
                expanded_parts = [mapping.get(p.lower(), p) for p in parts]

            return ', '.join(expanded_parts)

        # Aplica a função nas colunas
        final_df['nationality'] = final_df['nationality'].apply(lambda x: expand_abbreviations(x, nationality_map, case='lower'))
        final_df['position'] = final_df['position'].apply(lambda x: expand_abbreviations(x, position_map, case='upper'))
        
        # --- ETAPA 5.5: LIMPEZA DE DADOS NUMÉRICOS ---
        spider.logger.info("Limpando caracteres não numéricos das colunas de estatísticas...")
        
        id_cols_final_set = {'player', 'birth_date', 'nationality', 'position', 'team'}
        stat_cols_to_clean = [col for col in final_df.columns if col not in id_cols_final_set]

        for col in stat_cols_to_clean:
            if final_df[col].dtype == 'object':
                final_df[col] = final_df[col].str.replace(',', '', regex=False)

        # --- ETAPA 6: TRATAMENTO DOS TIPOS DE DADOS ---
        id_cols_final = ['player', 'birth_date', 'nationality', 'position', 'team']
        stat_cols_to_convert = [col for col in final_df.columns if col not in id_cols_final]
        for col in stat_cols_to_convert:
            final_df[col] = pd.to_numeric(final_df[col], errors='coerce')
        
        # --- ETAPA 7: PREENCHER CÉLULAS VAZIAS ---
        text_cols = ['player', 'birth_date', 'nationality', 'position', 'team']
        numeric_cols_to_fill = [col for col in final_df.columns if col not in text_cols]
        final_df[numeric_cols_to_fill] = final_df[numeric_cols_to_fill].fillna(0)

        # --- ETAPA 7.5: REMOÇÃO DE COLUNAS INDESEJADAS ---
        spider.logger.info("Removendo colunas desnecessárias do DataFrame final...")
        columns_to_drop = [
            'Advanced_Goalkeeping_matches', 'Advanced_Goalkeeping_minutes_90s', 'Advanced_Goalkeeping_ranker',
            'Defensive_Actions_matches', 'Defensive_Actions_minutes_90s', 'Defensive_Actions_ranker',
            'Goal_and_Shot_Creation_matches', 'Goal_and_Shot_Creation_minutes_90s', 'Goal_and_Shot_Creation_ranker',
            'Goalkeeping_matches', 'Goalkeeping_minutes_90s', 'Goalkeeping_ranker',
            'Miscellaneous_Stats_matches', 'Miscellaneous_Stats_minutes_90s', 'Miscellaneous_Stats_ranker',
            'Pass_Types_matches', 'Pass_Types_minutes_90s', 'Pass_Types_ranker',
            'Passing_matches', 'Passing_minutes_90s', 'Passing_ranker',
            'Playing_Time_matches', 'Playing_Time_ranker',
            'Possession_matches', 'Possession_minutes_90s', 'Possession_ranker',
            'Shooting_matches', 'Shooting_minutes_90s', 'Shooting_ranker'
        ]
        
        final_df.drop(columns=columns_to_drop, inplace=True, errors='ignore')

        # --- ETAPA 8: REORDENAÇÃO DAS COLUNAS ---
        spider.logger.info("Reordenando as colunas para a organização final...")
        final_ordered_columns = [col for col in id_cols_final if col in final_df.columns]
        stat_cols_ordered = sorted([col for col in final_df.columns if col not in final_ordered_columns])
        final_ordered_columns.extend(stat_cols_ordered)
        final_df = final_df[final_ordered_columns]
        
        # --- ETAPA 9: SALVAR O ARQUIVO FINAL ---
        output_filename = "fbref_player_stats_final.xlsx"
        final_df.to_excel(output_filename, index=False)
        spider.logger.info(f"Arquivo Excel final e organizado '{output_filename}' salvo com sucesso.")