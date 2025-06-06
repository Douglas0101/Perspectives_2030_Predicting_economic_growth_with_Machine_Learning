import pandas as pd
from pathlib import Path
import time


# Este script realiza o pré-processamento dos dados (ETL).
# Ele deve ser executado uma única vez ou sempre que os dados brutos forem atualizados.
# Ele lê os múltiplos arquivos CSV, limpa, transforma, combina os dados e salva
# um único arquivo Parquet otimizado para ser consumido pelo dashboard Streamlit.

def preprocess_data():
    """
    Função principal de ETL para preparar os dados do dashboard.
    """
    start_time = time.time()
    ROOT = Path(__file__).resolve().parent
    DATA_DIR = ROOT / "data"

    print("Iniciando o pré-processamento de dados...")

    # --- ETAPA 1: Ler os dados "prontos" para extrair mapeamentos ---
    # Este arquivo funciona como uma fonte de verdade para os mapeamentos de
    # continente, CAGR pré-calculado e códigos ISO.

    country_to_continent_map, country_to_cagr_map, country_to_iso_map = {}, {}, {}
    df_ready_path = DATA_DIR / "gdp_dashboard_ready_data.csv"

    try:
        print(f"Lendo '{df_ready_path.name}' para criar os mapeamentos...")
        df_ready = pd.read_csv(df_ready_path).rename(columns={"Entity": "Country"})

        # Mapeamento: País -> Continente
        country_to_continent_map = df_ready[['Country', 'Continent']].drop_duplicates('Country').set_index('Country')[
            'Continent'].to_dict()

        # Mapeamento: País -> CAGR (taxa de crescimento anual composta)
        df_ready_2030_cagr = df_ready[df_ready['Year'] == 2030]
        country_to_cagr_map = df_ready_2030_cagr.set_index('Country')['CAGR_Forecast'].to_dict()

        # Mapeamento: País -> Código ISO Alpha 3
        country_to_iso_map = \
        df_ready[['Country', 'ISO_Alpha3']].dropna().drop_duplicates('Country').set_index('Country')[
            'ISO_Alpha3'].to_dict()
        print("Mapeamentos criados com sucesso.")

    except FileNotFoundError:
        print(f"AVISO: Arquivo '{df_ready_path.name}' não encontrado. Mapeamentos estarão vazios.")
    except Exception as e:
        print(f"Erro ao processar '{df_ready_path.name}': {e}")

    # --- ETAPA 2: Processar dados históricos (`df_h`) ---
    try:
        df_h_path = DATA_DIR / "gdp_per_capita.csv"
        print(f"Lendo e processando dados históricos de '{df_h_path.name}'...")
        df_h = pd.read_csv(df_h_path)
        df_h = df_h.rename(columns={"Entity": "Country", "GDP per capita": "GDP_per_capita"})
        df_h = df_h[['Country', 'Year', 'GDP_per_capita']].copy()

        df_h['Type'] = "Historic"
        df_h['Continent'] = df_h["Country"].map(country_to_continent_map).fillna("Desconhecido")
        df_h['ISO_Alpha3'] = df_h["Country"].map(country_to_iso_map)  # Mapeia ISO para dados históricos

        df_h["Year"] = pd.to_numeric(df_h["Year"], errors='coerce')
        df_h["GDP_per_capita"] = pd.to_numeric(df_h["GDP_per_capita"], errors='coerce')

    except FileNotFoundError:
        print(f"ERRO CRÍTICO: Arquivo de dados históricos '{df_h_path.name}' não encontrado. Abortando.")
        return
    except Exception as e:
        print(f"Erro ao processar '{df_h_path.name}': {e}")
        return

    # --- ETAPA 3: Processar dados de previsão (`df_f`) ---
    try:
        df_f_path = DATA_DIR / "gdp_forecast_to_2030.csv"
        print(f"Lendo e processando dados de previsão de '{df_f_path.name}'...")
        df_f_raw = pd.read_csv(df_f_path)
        df_f = df_f_raw.rename(columns={"Entity": "Country", "GDP per capita": "GDP_per_capita"})

        # Filtra para o ano de 2030 e remove duplicatas
        df_f = df_f[df_f['Year'] == 2030].drop_duplicates(subset=['Country', 'Year'], keep='last').copy()

        df_f['Type'] = "Forecast"
        df_f['Continent'] = df_f["Country"].map(country_to_continent_map).fillna("Desconhecido")

        # Mapeamento especial de ISO para 'Eswatini', que pode estar como 'Swaziland' nos dados de mapeamento
        country_name_replacements = {"Eswatini": "Swaziland"}
        df_f['Country_for_ISO_map'] = df_f['Country'].replace(country_name_replacements)
        df_f["ISO_Alpha3"] = df_f["Country_for_ISO_map"].map(country_to_iso_map)
        df_f = df_f.drop(columns=['Country_for_ISO_map'])

        df_f["GDP_per_capita"] = pd.to_numeric(df_f["GDP_per_capita"], errors='coerce')

        # --- Cálculo do CAGR ---
        print("Calculando CAGR para dados de previsão...")
        # 1. Tenta preencher com valores do mapa pré-calculado
        df_f['CAGR'] = df_f["Country"].map(country_to_cagr_map)

        # 2. Para os que faltam, calcula dinamicamente
        latest_historical = df_h.loc[df_h.groupby('Country')['Year'].idxmax()][
            ['Country', 'Year', 'GDP_per_capita']
        ].rename(columns={'Year': 'Last_Hist_Year', 'GDP_per_capita': 'Last_Hist_GDP'})

        df_f_merged = pd.merge(df_f, latest_historical, on='Country', how='left')

        # Condições para o cálculo ser válido
        mask_cagr_null = df_f_merged['CAGR'].isnull()
        valid_calc_mask = (
                mask_cagr_null &
                df_f_merged['Last_Hist_GDP'].notna() & (df_f_merged['Last_Hist_GDP'] > 0) &
                df_f_merged['GDP_per_capita'].notna() &
                (df_f_merged['Year'] - df_f_merged['Last_Hist_Year']) > 0
        )

        # Aplica a fórmula do CAGR
        anos = df_f_merged.loc[valid_calc_mask, 'Year'] - df_f_merged.loc[valid_calc_mask, 'Last_Hist_Year']
        crescimento = (df_f_merged.loc[valid_calc_mask, 'GDP_per_capita'] / df_f_merged.loc[
            valid_calc_mask, 'Last_Hist_GDP'])

        df_f_merged.loc[valid_calc_mask, 'CAGR'] = (crescimento ** (1 / anos)) - 1

        # Atualiza a coluna CAGR no dataframe original e preenche NaNs restantes com 0
        df_f['CAGR'] = df_f_merged['CAGR']
        df_f['CAGR'] = pd.to_numeric(df_f['CAGR'], errors='coerce').fillna(0)

    except FileNotFoundError:
        print(f"ERRO CRÍTICO: Arquivo de previsão '{df_f_path.name}' não encontrado. Abortando.")
        return
    except Exception as e:
        print(f"Erro ao processar '{df_f_path.name}': {e}")
        return

    # --- ETAPA 4: Combinar DataFrames e Salvar ---
    print("Combinando dados históricos e de previsão...")

    # Selecionar e reordenar colunas para consistência
    cols_final = ['Country', 'Year', 'GDP_per_capita', 'Continent', 'Type', 'ISO_Alpha3', 'CAGR']
    df_h = df_h.reindex(columns=cols_final)  # CAGR ficará como NaN nos históricos, o que é correto
    df_f = df_f.reindex(columns=cols_final)

    # Concatena os dois dataframes
    df_final = pd.concat([df_h, df_f], ignore_index=True)

    # Limpeza final
    df_final.dropna(subset=['Year', 'GDP_per_capita', 'Country'], inplace=True)
    df_final["Year"] = df_final["Year"].astype('int32')
    df_final["GDP_per_capita"] = df_final["GDP_per_capita"].astype('float64')

    # Garantir que a pasta de dados exista
    DATA_DIR.mkdir(exist_ok=True)
    output_path = DATA_DIR / "dashboard_data.parquet"

    try:
        print(f"Salvando o arquivo de dados final em '{output_path}'...")
        df_final.to_parquet(output_path, index=False)
        processing_time = time.time() - start_time
        print("-" * 50)
        print(f"✅ Pré-processamento concluído com sucesso em {processing_time:.2f} segundos!")
        print(f"O arquivo '{output_path.name}' foi criado com {len(df_final)} linhas.")
        print("Agora você pode executar 'streamlit run app.py'.")
        print("-" * 50)

    except Exception as e:
        print(f"ERRO CRÍTICO: Não foi possível salvar o arquivo Parquet. Erro: {e}")


if __name__ == "__main__":
    preprocess_data()