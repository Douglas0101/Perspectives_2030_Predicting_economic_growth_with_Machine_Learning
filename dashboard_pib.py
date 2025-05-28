import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
import numpy as np  # Para cálculos de KPI

# --- CONFIGURAÇÃO INICIAL ---
CSV_PATH = 'data/gdp_dashboard_ready_data.csv'

# Nomes das colunas como estão no seu arquivo gdp_dashboard_ready_data.csv
COL_COUNTRY = 'Entity'
COL_YEAR = 'Year'
COL_VALUE = 'GDP_per_capita'
COL_STATUS = 'Type'
COL_CAGR = 'CAGR_Forecast'
COL_ISO = 'ISO_Alpha3'
COL_CONTINENT = 'Continent'

# DataFrame global para armazenar os dados carregados
df = pd.DataFrame()

# --- CARREGAMENTO E VALIDAÇÃO DOS DADOS ---
try:
    print(f"INFO: Tentando carregar o arquivo CSV de: {CSV_PATH}")
    df_loaded = pd.read_csv(CSV_PATH)
    print(f"INFO: Arquivo CSV '{CSV_PATH}' carregado com sucesso. Nomes das colunas originais:",
          df_loaded.columns.tolist())

    expected_cols = [COL_COUNTRY, COL_YEAR, COL_VALUE, COL_STATUS, COL_CAGR, COL_ISO, COL_CONTINENT]
    actual_columns = df_loaded.columns.tolist()
    missing_cols_msg = []

    for col_name in expected_cols:
        if col_name not in actual_columns:
            missing_cols_msg.append(f"'{col_name}'")

    if missing_cols_msg:
        print(
            f"ERRO DE MAPEAMENTO: As seguintes colunas esperadas não foram encontradas no CSV: {', '.join(missing_cols_msg)}.")
        print(f"Nomes das colunas disponíveis no seu CSV: {actual_columns}")
        print("Verifique os nomes na seção 'CONFIGURAÇÃO INICIAL' ou o conteúdo do CSV.")
    else:
        df = df_loaded  # Atribui ao df global
        print("INFO: Todas as colunas esperadas foram encontradas.")
        print(
            f"  País: {COL_COUNTRY}, Ano: {COL_YEAR}, Valor: {COL_VALUE}, Status: {COL_STATUS}, CAGR: {COL_CAGR}, ISO: {COL_ISO}, Continente: {COL_CONTINENT}")

        # Conversão de tipos e tratamento de NaNs para colunas essenciais
        df[COL_YEAR] = pd.to_numeric(df[COL_YEAR], errors='coerce')
        df[COL_VALUE] = pd.to_numeric(df[COL_VALUE], errors='coerce')
        if COL_CAGR in df.columns:  # Converte CAGR apenas se a coluna existir
            df[COL_CAGR] = pd.to_numeric(df[COL_CAGR], errors='coerce')

        df[COL_COUNTRY] = df[COL_COUNTRY].astype(str)
        df[COL_STATUS] = df[COL_STATUS].astype(str)
        if COL_CONTINENT in df.columns:  # Converte Continente apenas se a coluna existir
            df[COL_CONTINENT] = df[COL_CONTINENT].astype(str)
        if COL_ISO in df.columns:  # Converte ISO apenas se a coluna existir
            df[COL_ISO] = df[COL_ISO].astype(str)

        # Remove linhas onde colunas numéricas CHAVE para plotagem são NaN após a conversão
        df.dropna(subset=[COL_YEAR, COL_VALUE], inplace=True)

except FileNotFoundError:
    print(f"ERRO CRÍTICO: Arquivo CSV não encontrado em '{CSV_PATH}'. O dashboard não funcionará sem dados.")
except Exception as e:
    print(f"ERRO CRÍTICO ao ler ou processar o CSV: {e}. O dashboard pode não funcionar corretamente.")

# --- INICIALIZAÇÃO DO APP DASH ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.ZEPHYR],
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}],
                suppress_callback_exceptions=True)  # Importante para layouts dinâmicos
server = app.server
app.title = "PIB per Capita 2030"

# --- PALETA DE CORES E ESTILOS ---
colors = {
    'background': '#F0F2F5', 'card_background': '#FFFFFF', 'text': '#2C3E50',
    'primary_color': '#007BFF', 'secondary_color': '#6C757D', 'accent_color_1': '#28A745',
    'accent_color_2': '#DC3545', 'grid_lines': '#DEE2E6', 'kpi_value': '#17A2B8'
}
KPI_CARD_BODY_STYLE = {
    'textAlign': 'center',
    'padding': '10px'
}
KPI_LABEL_STYLE = {'fontSize': '0.9em', 'color': colors['secondary_color']}
KPI_VALUE_STYLE = {'fontSize': '1.5em', 'fontWeight': 'bold', 'color': colors['kpi_value']}


# --- FUNÇÕES AUXILIARES ---
def create_kpi_card(label, value_id):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.H6(label, style=KPI_LABEL_STYLE),
                html.H4(id=value_id, style=KPI_VALUE_STYLE)
            ], style=KPI_CARD_BODY_STYLE),
            className="shadow-sm"
        ), xs=12, sm=6, md=4, lg=3, className="mb-3"
    )


def get_filtered_data_2030(selected_countries=None, selected_continents=None):
    if df.empty:
        return pd.DataFrame()  # Retorna DataFrame vazio se o global df estiver vazio

    df_filtered = df.copy()

    if selected_continents and COL_CONTINENT in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[COL_CONTINENT].isin(selected_continents)]

    if selected_countries and COL_COUNTRY in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[COL_COUNTRY].isin(selected_countries)]

    # Prepara para retornar um DataFrame vazio se nenhuma condição for atendida abaixo
    df_2030_final = pd.DataFrame(columns=df_filtered.columns)

    status_forecast_values = ['Forecast', 'Previsão', 'Prediction', 'Projeção']

    if COL_STATUS in df_filtered.columns and COL_YEAR in df_filtered.columns:
        df_2030_forecast = df_filtered[
            (df_filtered[COL_YEAR] == 2030) &
            (df_filtered[COL_STATUS].str.contains('|'.join(status_forecast_values), case=False, na=False))
            ]
        if not df_2030_forecast.empty:
            df_2030_final = df_2030_forecast
        else:  # Fallback se 'Forecast' não for encontrado, mas há dados para 2030
            df_2030_any = df_filtered[df_filtered[COL_YEAR] == 2030]
            if not df_2030_any.empty:
                df_2030_final = df_2030_any
    elif COL_YEAR in df_filtered.columns:  # Se não há COL_STATUS, mas há COL_YEAR
        df_2030_any = df_filtered[df_filtered[COL_YEAR] == 2030]
        if not df_2030_any.empty:
            df_2030_final = df_2030_any

    return df_2030_final


# --- LAYOUT DO DASHBOARD ---
app.layout = dbc.Container(fluid=True,
                           style={'backgroundColor': colors['background'], 'color': colors['text'], 'padding': '20px'},
                           children=[
                               dbc.Row(dbc.Col(html.H1(app.title, className="text-center mb-2",
                                                       style={'color': colors['primary_color'], 'fontWeight': 'bold'}),
                                               width=12)),
                               dbc.Row(dbc.Col(html.P(
                                   "Análise interativa da evolução e projeção do Produto Interno Bruto per capita.",
                                   className="text-center mb-4 lead", style={'color': colors['text']}), width=12)),
                               dbc.Row([
                                   dbc.Col(dbc.Card(dbc.CardBody([
                                       html.H5("Filtros Globais", className="card-title text-center",
                                               style={'color': colors['primary_color']}),
                                       dbc.Row([
                                           dbc.Col(dcc.Dropdown(id='continent-dropdown',
                                                                options=[{'label': str(cont), 'value': str(cont)} for
                                                                         cont in sorted(df[
                                                                                            COL_CONTINENT].unique())] if COL_CONTINENT in df.columns and not df.empty else [],
                                                                multi=True, placeholder="Selecione Continente(s)",
                                                                className="mb-2"), md=6),
                                           dbc.Col(dcc.Dropdown(id='country-dropdown', multi=True,
                                                                placeholder="Selecione País(es)", className="mb-2"),
                                                   md=6),
                                       ]),
                                   ]), className="shadow-sm mb-4"), width=12)
                               ]),
                               dbc.Row(id='kpi-row', className="mb-3", children=[
                                   create_kpi_card("Maior PIB/cap 2030", "kpi-max-gdp"),
                                   create_kpi_card("País (Maior PIB)", "kpi-max-gdp-country"),
                                   create_kpi_card("Média PIB/cap 2030 (Sel.)", "kpi-avg-gdp"),
                                   create_kpi_card("País Maior CAGR", "kpi-max-cagr-country"),
                               ]),
                               html.Div(id='dashboard-main-content'),  # Conteúdo dinâmico dos gráficos e tabela
                               dbc.Row(dbc.Col(html.Footer(html.P(
                                   f"Projeto de Finanças em Data Science com IA. Dados atualizados até {pd.to_datetime('today').strftime('%Y-%m-%d')}.",
                                   className="text-center text-muted small mt-5")), width=12))
                           ])


# --- CALLBACKS ---
@app.callback(
    Output('country-dropdown', 'options'),
    Output('country-dropdown', 'value'),  # Limpa seleção de país ao mudar continente
    Input('continent-dropdown', 'value'),
    prevent_initial_call=True  # Não executa na carga inicial se não houver seleção de continente
)
def update_country_dropdown(selected_continents):
    if df.empty or COL_CONTINENT not in df.columns or COL_COUNTRY not in df.columns:
        return [], []

    filtered_df_for_countries = df.copy()
    if selected_continents:  # Se algum continente for selecionado
        filtered_df_for_countries = df[df[COL_CONTINENT].isin(selected_continents)]

    country_options = [{'label': str(country), 'value': str(country)} for country in
                       sorted(filtered_df_for_countries[COL_COUNTRY].unique())]
    return country_options, []  # Limpa valor para forçar nova seleção ou deixar vazio


@app.callback(
    Output('dashboard-main-content', 'children'),
    Input('country-dropdown', 'value'),
    Input('continent-dropdown', 'value')
)
def render_main_content(selected_countries, selected_continents):
    if df.empty:
        return dbc.Alert("Os dados não foram carregados ou são inválidos. Verifique os logs do console.",
                         color="danger", className="mt-3")
    # Mostra conteúdo apenas se houver alguma seleção de filtro
    if not selected_countries and not selected_continents:
        return dbc.Alert("Por favor, selecione continentes e/ou países para visualizar os dados.", color="info",
                         className="mt-3")

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Evolução do PIB per Capita (Histórico e Previsão)", className="card-title text-center",
                        style={'color': colors['primary_color']}),
                dcc.Loading(id="loading-line-chart", type="default",
                            children=dcc.Graph(id='gdp-line-chart', figure=px.line(title="Aguardando seleção...")))
                # Figura placeholder
            ]), className="shadow-sm mb-4"), width=12)
        ]),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("PIB per Capita Previsto para 2030", className="card-title text-center",
                        style={'color': colors['primary_color']}),
                dcc.Loading(id="loading-bar-chart", type="default",
                            children=dcc.Graph(id='gdp-bar-chart-2030', figure=px.bar(title="Aguardando seleção...")))
                # Figura placeholder
            ]), className="shadow-sm mb-4"), width=12)
        ]),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Dados Detalhados (Previsão 2030)", className="card-title text-center",
                        style={'color': colors['primary_color']}),
                html.Div(id='gdp-table-2030', children=dbc.Alert("Aguardando seleção...", color="light"))
                # Conteúdo placeholder
            ]), className="shadow-sm mb-4"), width=12)
        ])
    ])


@app.callback(
    Output('kpi-max-gdp', 'children'),
    Output('kpi-max-gdp-country', 'children'),
    Output('kpi-avg-gdp', 'children'),
    Output('kpi-max-cagr-country', 'children'),
    Input('country-dropdown', 'value'),
    Input('continent-dropdown', 'value')
)
def update_kpis(selected_countries, selected_continents):
    default_kpi_value = "N/A"
    if df.empty:
        return default_kpi_value, default_kpi_value, default_kpi_value, default_kpi_value

    # Só processa se houver alguma seleção de filtro
    if not selected_countries and not selected_continents:
        return default_kpi_value, default_kpi_value, default_kpi_value, default_kpi_value

    df_2030 = get_filtered_data_2030(selected_countries, selected_continents)

    if df_2030.empty:
        return default_kpi_value, default_kpi_value, default_kpi_value, default_kpi_value

    # KPI: Maior PIB/cap 2030 e País
    max_gdp_val = df_2030[COL_VALUE].max()
    max_gdp_country_val = default_kpi_value
    if not pd.isna(max_gdp_val) and COL_COUNTRY in df_2030.columns:
        countries_with_max_gdp = df_2030.loc[df_2030[COL_VALUE] == max_gdp_val, COL_COUNTRY]
        if not countries_with_max_gdp.empty:
            max_gdp_country_val = countries_with_max_gdp.iloc[0]

    # KPI: Média PIB/cap 2030 (Sel.)
    avg_gdp_val = df_2030[COL_VALUE].mean()

    # KPI: País Maior CAGR
    max_cagr_display = default_kpi_value
    if COL_CAGR in df_2030.columns and df_2030[COL_CAGR].notna().any():
        max_cagr_val = df_2030[COL_CAGR].max()
        if not pd.isna(max_cagr_val):
            max_cagr_rows = df_2030[(df_2030[COL_CAGR] == max_cagr_val) & (df_2030[COL_CAGR].notna())]
            if not max_cagr_rows.empty:
                max_cagr_country_row = max_cagr_rows.iloc[0]
                if COL_COUNTRY in max_cagr_country_row:
                    max_cagr_country_name = max_cagr_country_row[COL_COUNTRY]
                    max_cagr_display = f"{max_cagr_country_name} ({max_cagr_val:.2%})"

    return (
        f"${max_gdp_val:,.0f}" if not pd.isna(max_gdp_val) else default_kpi_value,
        str(max_gdp_country_val),
        f"${avg_gdp_val:,.0f}" if not pd.isna(avg_gdp_val) else default_kpi_value,
        str(max_cagr_display)
    )


@app.callback(
    Output('gdp-line-chart', 'figure'),
    Input('country-dropdown', 'value'),
    Input('continent-dropdown', 'value')
)
def update_line_chart(selected_countries, selected_continents):
    fig_placeholder = px.line(title="Selecione filtros para visualizar os dados.")
    if df.empty: return fig_placeholder
    if not selected_countries and not selected_continents: return fig_placeholder

    df_plot = df.copy()
    if selected_continents and COL_CONTINENT in df_plot.columns:
        df_plot = df_plot[df_plot[COL_CONTINENT].isin(selected_continents)]
    if selected_countries and COL_COUNTRY in df_plot.columns:
        df_plot = df_plot[df_plot[COL_COUNTRY].isin(selected_countries)]
    else:  # Se países não estão selecionados mas continentes estão, usa o df_plot filtrado por continente
        if not selected_continents:  # Se realmente nada foi selecionado (deveria ser pego antes)
            return fig_placeholder

    if df_plot.empty: return px.line(title="Nenhum dado encontrado para a seleção atual.")

    fig = px.line(
        df_plot, x=COL_YEAR, y=COL_VALUE, color=COL_COUNTRY, line_dash=COL_STATUS,
        markers=False,
        labels={COL_VALUE: 'PIB per Capita (USD)', COL_YEAR: 'Ano', COL_COUNTRY: 'País', COL_STATUS: 'Tipo'},
        title="Evolução do PIB per Capita"
    )
    fig.update_layout(plot_bgcolor=colors['card_background'], paper_bgcolor=colors['card_background'],
                      font_color=colors['text'], xaxis_gridcolor=colors['grid_lines'],
                      yaxis_gridcolor=colors['grid_lines'], legend_title_text='Legenda', hovermode="x unified",
                      margin=dict(l=40, r=20, t=60, b=30))  # Ajuste de margens
    fig.update_traces(line=dict(width=2))
    return fig


@app.callback(
    Output('gdp-bar-chart-2030', 'figure'),
    Input('country-dropdown', 'value'),
    Input('continent-dropdown', 'value')
)
def update_bar_chart_2030(selected_countries, selected_continents):
    fig_placeholder = px.bar(title="Selecione filtros para visualizar os dados.")
    if df.empty: return fig_placeholder
    if not selected_countries and not selected_continents: return fig_placeholder

    df_2030 = get_filtered_data_2030(selected_countries, selected_continents)
    if df_2030.empty: return px.bar(title="Nenhum dado de previsão para 2030 para a seleção atual.")

    fig = px.bar(
        df_2030.sort_values(by=COL_VALUE, ascending=False), x=COL_COUNTRY, y=COL_VALUE, color=COL_COUNTRY,
        labels={COL_VALUE: 'PIB per Capita Previsto (USD)', COL_COUNTRY: 'País'},
        title="PIB per Capita Previsto para 2030"
    )
    fig.update_layout(plot_bgcolor=colors['card_background'], paper_bgcolor=colors['card_background'],
                      font_color=colors['text'], xaxis_title=None, yaxis_title="PIB per Capita (USD)", showlegend=False,
                      margin=dict(l=40, r=20, t=60, b=30))
    fig.update_traces(marker_line_width=1, marker_line_color='rgba(0,0,0,0.7)')
    return fig


@app.callback(
    Output('gdp-table-2030', 'children'),
    Input('country-dropdown', 'value'),
    Input('continent-dropdown', 'value')
)
def update_table_2030(selected_countries, selected_continents):
    alert_placeholder = dbc.Alert("Selecione filtros para visualizar os dados.", color="info")
    if df.empty: return alert_placeholder
    if not selected_countries and not selected_continents: return alert_placeholder

    df_table_data = get_filtered_data_2030(selected_countries, selected_continents)
    if df_table_data.empty: return dbc.Alert("Nenhum dado de previsão para 2030 para a seleção.", color="warning")

    cols_to_display_orig = [COL_COUNTRY, COL_CONTINENT, COL_VALUE, COL_CAGR, COL_STATUS]
    cols_to_display = [col for col in cols_to_display_orig if col in df_table_data.columns]
    df_display = df_table_data[cols_to_display].copy()

    rename_map = {
        COL_COUNTRY: 'País', COL_CONTINENT: 'Continente', COL_VALUE: 'PIB/cap 2030 (USD)',
        COL_CAGR: 'CAGR Previsão', COL_STATUS: 'Tipo'
    }
    df_display.rename(columns={k: v for k, v in rename_map.items() if k in df_display.columns}, inplace=True)

    if 'CAGR Previsão' in df_display.columns:
        df_display['CAGR Previsão'] = df_display['CAGR Previsão'].apply(
            lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    if 'PIB/cap 2030 (USD)' in df_display.columns:
        df_display['PIB/cap 2030 (USD)'] = df_display['PIB/cap 2030 (USD)'].apply(
            lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")

    return dash_table.DataTable(
        data=df_display.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in df_display.columns],
        style_table={'overflowX': 'auto', 'maxHeight': '400px', 'overflowY': 'auto'},
        style_header={'backgroundColor': colors['primary_color'], 'color': 'white', 'fontWeight': 'bold'},
        style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '100px', 'width': '150px', 'maxWidth': '200px',
                    'whiteSpace': 'normal', 'height': 'auto', 'border': '1px solid #eee'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        page_size=10, sort_action="native", filter_action="native", export_format="csv",
    )


# --- EXECUÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    print("INFO: Iniciando o servidor Dash...")
    if df.empty:
        print(
            "ALERTA CRÍTICO: DataFrame global 'df' está vazio. Verifique o carregamento do CSV e os nomes das colunas.")
    app.run(debug=True, host='0.0.0.0', port=8050)