from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Variáveis globais para armazenar o dataframe e a lista de indicadores
dataframe = pd.DataFrame()
lista_indicadores_adicionais_globais = []


def load_data():
    global dataframe  # Indicar que estamos usando a variável global
    global lista_indicadores_adicionais_globais

    csv_file_path = os.path.join(DATA_DIR, 'gdp_dashboard_ready_data.csv')
    try:
        df_original = pd.read_csv(csv_file_path)
        print(f"Arquivo CSV '{csv_file_path}' carregado com sucesso.")
    except FileNotFoundError:
        print(f"ERRO: O arquivo '{csv_file_path}' NÃO FOI ENCONTRADO. Usando dados de exemplo.")
        data_exemplo = {
            'Entity': ['Brasil', 'Brasil', 'Argentina', 'Argentina', 'Afeganistão', 'Afeganistão', 'Estados Unidos',
                       'Estados Unidos', 'China', 'China', 'Índia', 'Índia'],
            'Year': [2018, 2019, 2018, 2019, 2018, 2019, 2018, 2019, 2018, 2019, 2018, 2019],
            'GDP_per_capita': [8920, 8717, 11794, 10560, 524, 502, 62823, 65111, 9770, 10261, 2010, 2100],
            'Population': [209.5, 211.0, 44.27, 44.78, 37.17, 38.04, 327.0, 328.2, 1393.0, 1398.0, 1353.0, 1366.0],
            # Exemplo de outro indicador
            'GDP_Growth_Rate': [1.8, 1.1, -2.5, -2.1, 1.0, 2.3, 2.9, 2.3, 6.7, 6.1, 6.8, 6.1],  # Exemplo
            'Type': ['País', 'País', 'País', 'País', 'País', 'País', 'País', 'País', 'País', 'País', 'País', 'País'],
            'CAGR_Forecast': [0.02, 0.015, 0.01, 0.018, 0.03, 0.025, 0.01, 0.012, 0.05, 0.045, 0.06, 0.065],
            'ISO_Alpha3': ['BRA', 'BRA', 'ARG', 'ARG', 'AFG', 'AFG', 'USA', 'USA', 'CHN', 'CHN', 'IND', 'IND'],
            'Continent': ['América do Sul', 'América do Sul', 'América do Sul', 'América do Sul', 'Ásia', 'Ásia',
                          'América do Norte', 'América do Norte', 'Ásia', 'Ásia']
        }
        df_original = pd.DataFrame(data_exemplo)

    df = df_original.copy()
    # Renomear colunas ANTES de identificar indicadores
    colunas_renomear = {'Entity': 'Pais', 'Year': 'Ano', 'GDP_per_capita': 'PIB_per_Capita'}
    # Adicionar outros mapeamentos se necessário, ex: 'Population': 'Populacao'
    df.rename(columns=colunas_renomear, inplace=True)

    # Identificar indicadores adicionais (colunas numéricas que não são as primárias)
    colunas_primarias = ['Pais', 'Ano', 'PIB_per_Capita']
    colunas_nao_indicadores = ['ISO_Alpha3', 'Continent', 'Type']  # Colunas categóricas ou de ID

    temp_indicadores = []
    for col in df.columns:
        if col not in colunas_primarias and col not in colunas_nao_indicadores:
            if pd.api.types.is_numeric_dtype(df[col]):
                temp_indicadores.append(col)
    lista_indicadores_adicionais_globais = sorted(temp_indicadores)

    # Limpeza de dados
    if 'Ano' in df.columns:
        df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce')
        df.dropna(subset=['Ano'], inplace=True)
        if not df['Ano'].empty:
            df['Ano'] = df['Ano'].astype(np.int64)
    else:
        if not df.empty: df['Ano'] = pd.Series(dtype=np.int64)

    if 'PIB_per_Capita' in df.columns:
        df['PIB_per_Capita'] = pd.to_numeric(df['PIB_per_Capita'], errors='coerce')
        df.dropna(subset=['PIB_per_Capita'], inplace=True)
    else:
        if not df.empty: df['PIB_per_Capita'] = pd.Series(dtype=float)

    dataframe = df  # Atribui à variável global
    return dataframe


dataframe = load_data()  # Carrega os dados na inicialização do app


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/paises')
def get_paises():
    if 'Pais' in dataframe.columns and not dataframe['Pais'].dropna().empty:
        paises = sorted(dataframe['Pais'].dropna().unique().tolist())
        return jsonify(paises)
    return jsonify([])


@app.route('/api/anos_range')
def get_anos_range():
    if 'Ano' in dataframe.columns and not dataframe['Ano'].dropna().empty:
        anos_validos = dataframe['Ano'].dropna()
        if not anos_validos.empty:
            min_ano = int(anos_validos.min())
            max_ano = int(anos_validos.max())
            return jsonify({'min_ano': min_ano, 'max_ano': max_ano})
    return jsonify({'min_ano': 2000, 'max_ano': 2020})


# NOVA ROTA PARA LISTA DE INDICADORES ADICIONAIS
@app.route('/api/lista_indicadores')
def get_lista_indicadores():
    return jsonify(lista_indicadores_adicionais_globais)


def filter_dataframe(df_input, paises_selecionados_str, min_ano_str, max_ano_str):
    df_processado = df_input.copy()
    if paises_selecionados_str and 'Pais' in df_processado.columns:
        lista_paises_selecionados = paises_selecionados_str.split(',')
        df_processado = df_processado[df_processado['Pais'].isin(lista_paises_selecionados)]

    if min_ano_str and 'Ano' in df_processado.columns:
        try:
            min_ano = int(min_ano_str); df_processado = df_processado[df_processado['Ano'] >= min_ano]
        except ValueError:
            pass

    if max_ano_str and 'Ano' in df_processado.columns:
        try:
            max_ano = int(max_ano_str); df_processado = df_processado[df_processado['Ano'] <= max_ano]
        except ValueError:
            pass
    return df_processado


@app.route('/api/dados_filtrados_completos')  # ROTA ATUALIZADA PARA DADOS COMPLETOS
def get_dados_filtrados_completos():
    paises_selecionados_str = request.args.get('paises', default=None, type=str)
    min_ano_str = request.args.get('minAno', default=None, type=str)
    max_ano_str = request.args.get('maxAno', default=None, type=str)

    df_filtrado = filter_dataframe(dataframe, paises_selecionados_str, min_ano_str, max_ano_str)

    if not df_filtrado.empty:
        # Garantir tipos corretos antes de converter para dicionário
        # Manter todas as colunas originais (após renomeação)
        for col in df_filtrado.columns:
            if df_filtrado[col].dtype == 'float64':
                # Arredondar floats para um número razoável de casas decimais para JSON
                df_filtrado[col] = df_filtrado[col].round(3)
            elif df_filtrado[col].dtype == 'int64':
                df_filtrado[col] = df_filtrado[col].astype(int)  # Converte para int Python nativo

        # Substituir NaNs por strings vazias ou 'N/A' para melhor visualização no JSON/tabela
        df_filtrado_json = df_filtrado.fillna('N/A')
        data_to_return = df_filtrado_json.to_dict(orient='records')
        return jsonify(data_to_return)
    return jsonify([])


@app.route('/api/estatisticas_pib')
def get_estatisticas_pib():
    paises_selecionados_str = request.args.get('paises', default=None, type=str)
    min_ano_str = request.args.get('minAno', default=None, type=str)
    max_ano_str = request.args.get('maxAno', default=None, type=str)

    df_filtrado = filter_dataframe(dataframe, paises_selecionados_str, min_ano_str, max_ano_str)

    estatisticas_lista = []
    if not df_filtrado.empty and 'Pais' in df_filtrado.columns and 'PIB_per_Capita' in df_filtrado.columns and 'Ano' in df_filtrado.columns:
        paises_no_filtro = df_filtrado['Pais'].unique()
        for pais in paises_no_filtro:
            df_pais_stats = df_filtrado[df_filtrado['Pais'] == pais]
            if not df_pais_stats['PIB_per_Capita'].empty:
                pib_col = df_pais_stats['PIB_per_Capita'].dropna()  # Remover NaNs antes de calcular estatísticas
                if pib_col.empty: continue  # Pular se não houver dados válidos de PIB

                df_pais_stats_sorted_anos = df_pais_stats.sort_values(by='Ano')
                pib_sorted_anos = df_pais_stats_sorted_anos['PIB_per_Capita'].dropna()

                variacao = np.nan
                if len(pib_sorted_anos) > 1:
                    variacao = pib_sorted_anos.iloc[-1] - pib_sorted_anos.iloc[0]

                estatisticas_lista.append({
                    'País': pais,
                    'Média': round(pib_col.mean(), 2) if pd.notnull(pib_col.mean()) else 'N/A',
                    'Mediana': round(pib_col.median(), 2) if pd.notnull(pib_col.median()) else 'N/A',
                    'Desvio Padrão': round(pib_col.std(), 2) if pd.notnull(pib_col.std()) else 'N/A',
                    'Mínimo': round(pib_col.min(), 2) if pd.notnull(pib_col.min()) else 'N/A',
                    'Máximo': round(pib_col.max(), 2) if pd.notnull(pib_col.max()) else 'N/A',
                    'Variação no Período': round(variacao, 2) if pd.notnull(variacao) else 'N/A'
                })
    return jsonify(estatisticas_lista)


if __name__ == '__main__':
    # ... (código de verificação de pastas static, se desejar manter) ...
    app.run(debug=True, port=5001)
