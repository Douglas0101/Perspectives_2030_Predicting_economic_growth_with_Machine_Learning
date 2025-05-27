import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Previsão de PIB per Capita Global",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Constantes para nomes de colunas
class ColNames:
    ENTITY = 'Entity'
    YEAR = 'Year'
    GDP_PER_CAPITA = 'GDP_per_capita'
    TYPE = 'Type'
    ISO_ALPHA3 = 'ISO_Alpha3'
    CONTINENT = 'Continent'
    CAGR = 'CAGR_Forecast'


@st.cache_data
def load_data(file_path):
    """Carrega e pré-processa minimamente os dados para o dashboard."""
    try:
        df = pd.read_csv(file_path)

        df[ColNames.YEAR] = pd.to_numeric(df[ColNames.YEAR], errors='coerce')
        df[ColNames.GDP_PER_CAPITA] = pd.to_numeric(df[ColNames.GDP_PER_CAPITA], errors='coerce')
        df[ColNames.CAGR] = pd.to_numeric(df[ColNames.CAGR], errors='coerce')

        df.dropna(subset=[ColNames.YEAR, ColNames.GDP_PER_CAPITA], inplace=True)

        df[ColNames.ENTITY] = df[ColNames.ENTITY].astype(str)
        df[ColNames.TYPE] = df[ColNames.TYPE].astype(str)
        df[ColNames.ISO_ALPHA3] = df[ColNames.ISO_ALPHA3].fillna('N/A')
        df[ColNames.CONTINENT] = df[ColNames.CONTINENT].fillna('Desconhecido/Agregado')

        return df
    except FileNotFoundError:
        st.error(
            f"ERRO: O ficheiro de dados '{file_path}' não foi encontrado. Certifique-se de que o script de preparação de dados ('prepare_dashboard_data.py') foi executado e o ficheiro 'gdp_dashboard_ready_data.csv' está na pasta 'data'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados: {e}")
        return pd.DataFrame()


# --- Carregamento dos Dados ---
DATA_FILE_PATH = os.path.join('data', 'gdp_dashboard_ready_data.csv')
df_dashboard = load_data(DATA_FILE_PATH)

# --- Métricas do Modelo ---
MODEL_MAE = 178.14
MODEL_MSE = 937336.69
MODEL_R2 = 0.9885
LAST_HISTORICAL_YEAR_OVERALL = df_dashboard[df_dashboard[ColNames.TYPE] == 'Historical'][
    ColNames.YEAR].max() if not df_dashboard.empty and ColNames.YEAR in df_dashboard.columns else "N/A"
FORECAST_END_YEAR = 2030

# --- Sidebar para Filtros Globais ---
st.sidebar.header("Filtros Globais 🌍")

all_continents_option = "Todos os Continentes"
if not df_dashboard.empty and ColNames.CONTINENT in df_dashboard.columns:
    continent_options = sorted(
        [c for c in df_dashboard[ColNames.CONTINENT].unique() if c not in ['World', 'Desconhecido/Agregado']])
    selected_continent = st.sidebar.selectbox(
        "Selecione o Continente:",
        options=[all_continents_option] + continent_options,
        index=0
    )
    if selected_continent == all_continents_option:
        filtered_df_by_continent = df_dashboard.copy()
    else:
        filtered_df_by_continent = df_dashboard[df_dashboard[ColNames.CONTINENT] == selected_continent]
else:
    filtered_df_by_continent = df_dashboard.copy()

if not filtered_df_by_continent.empty and ColNames.YEAR in filtered_df_by_continent.columns:
    forecast_years = sorted(filtered_df_by_continent[filtered_df_by_continent[ColNames.TYPE] == 'Forecast'][
                                ColNames.YEAR].unique().tolist())
    if not forecast_years:
        forecast_years = sorted(
            df_dashboard[df_dashboard[ColNames.TYPE] == 'Forecast'][ColNames.YEAR].unique().tolist())

    default_year_index = len(forecast_years) - 1 if forecast_years else 0
    if forecast_years:
        selected_year_global = st.sidebar.selectbox(
            "Selecione o Ano para Visão Global:",
            options=forecast_years,
            index=default_year_index
        )
    else:
        selected_year_global = None
        st.sidebar.warning("Não há anos de previsão disponíveis com os filtros atuais.")
else:
    selected_year_global = None

# --- Layout da Aplicação ---
st.title("🌍 Dashboard de Previsão do PIB per Capita Global")
st.markdown(f"""
Este dashboard apresenta uma análise do Produto Interno Bruto (PIB) per capita histórico e previsões até **{FORECAST_END_YEAR}**.
Utilize os filtros na barra lateral e as visualizações interativas para explorar as tendências econômicas.
O modelo de previsão subjacente é um LSTM (Keras) otimizado.
""")

st.header("Visão Geral e Performance do Modelo 📊")
if not df_dashboard.empty:
    num_countries_analyzed = df_dashboard[
        (df_dashboard[ColNames.ISO_ALPHA3] != 'N/A') & (
            ~df_dashboard[ColNames.ISO_ALPHA3].str.startswith('OWID_', na=False))
        ][ColNames.ENTITY].nunique()
else:
    num_countries_analyzed = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Países Individuais Analisados", f"~{num_countries_analyzed}")
col2.metric("Previsões Até", str(FORECAST_END_YEAR))
col3.metric("MAE Modelo LSTM (Teste)", f"${MODEL_MAE:,.2f}")
col4.metric("R² Modelo LSTM (Teste)", f"{MODEL_R2:.4f}")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Séries Temporais por Entidade", "Rankings e CAGR", "Visão Global (Mapa)", "Sobre o Modelo"])

with tab1:
    st.subheader("Série Temporal: PIB per Capita (Histórico e Previsão)")
    if not filtered_df_by_continent.empty:
        entities_for_line_chart = sorted(filtered_df_by_continent[ColNames.ENTITY].unique().tolist())
        default_entities = [e for e in entities_for_line_chart if not e.endswith("(MPD)") and e != "World"]
        if not default_entities and entities_for_line_chart:
            default_entities = entities_for_line_chart[:1]
        elif not entities_for_line_chart:
            default_entities = []

        selected_entities_line = st.multiselect(
            "Selecione até 5 Países/Entidades para visualizar a série temporal:",
            options=entities_for_line_chart,
            default=default_entities[:min(len(default_entities), 1)],
            max_selections=5
        )

        if selected_entities_line:
            df_line_chart = filtered_df_by_continent[
                filtered_df_by_continent[ColNames.ENTITY].isin(selected_entities_line)]
            fig_line = px.line(
                df_line_chart, x=ColNames.YEAR, y=ColNames.GDP_PER_CAPITA, color=ColNames.ENTITY,
                line_dash=ColNames.TYPE, title="PIB per Capita: Histórico vs. Previsão",
                labels={ColNames.GDP_PER_CAPITA: "PIB per Capita (USD)", ColNames.YEAR: "Ano"}, markers=True
            )
            fig_line.update_layout(legend_title_text='Entidade/Tipo')
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Por favor, selecione pelo menos uma entidade para visualizar a série temporal.")
    else:
        st.warning("Não há dados disponíveis para os filtros selecionados.")

with tab2:
    st.subheader(f"Ranking de Entidades e CAGR Previsto (Último Histórico até {FORECAST_END_YEAR})")
    if not filtered_df_by_continent.empty and ColNames.CAGR in filtered_df_by_continent.columns:
        ranking_data_list = []
        for entity, group in filtered_df_by_continent.groupby(ColNames.ENTITY):
            hist_data = group[group[ColNames.TYPE] == 'Historical']
            forecast_data_end_year = group[
                (group[ColNames.TYPE] == 'Forecast') & (group[ColNames.YEAR] == FORECAST_END_YEAR)]

            last_hist_year_val = hist_data[ColNames.YEAR].max() if not hist_data.empty else np.nan
            last_hist_gdp_val = hist_data[hist_data[ColNames.YEAR] == last_hist_year_val][ColNames.GDP_PER_CAPITA].iloc[
                0] if not hist_data.empty and pd.notna(last_hist_year_val) else np.nan
            forecast_gdp_val = forecast_data_end_year[ColNames.GDP_PER_CAPITA].iloc[
                0] if not forecast_data_end_year.empty else np.nan
            cagr_val = group[ColNames.CAGR].iloc[0] if ColNames.CAGR in group.columns and not group[
                ColNames.CAGR].empty and pd.notna(group[ColNames.CAGR].iloc[0]) else np.nan

            # Adicionar ISO_Alpha3 ao dicionário
            iso_alpha3_val = group[ColNames.ISO_ALPHA3].iloc[0] if ColNames.ISO_ALPHA3 in group.columns and not group[
                ColNames.ISO_ALPHA3].empty else 'N/A'

            ranking_data_list.append({
                ColNames.ENTITY: entity,
                'Último Ano Histórico': int(last_hist_year_val) if pd.notna(last_hist_year_val) else 'N/A',
                'PIB Histórico (Último Ano)': last_hist_gdp_val,
                f"PIB Previsto ({FORECAST_END_YEAR})": forecast_gdp_val,
                ColNames.CAGR: cagr_val,
                ColNames.ISO_ALPHA3: iso_alpha3_val  # Adicionado ISO_ALPHA3
            })

        if ranking_data_list:
            ranking_df = pd.DataFrame(ranking_data_list)
            ranking_df[ColNames.CAGR] = ranking_df[ColNames.CAGR].map(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
            ranking_df[f"PIB Previsto ({FORECAST_END_YEAR})"] = ranking_df[f"PIB Previsto ({FORECAST_END_YEAR})"].map(
                lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")
            ranking_df["PIB Histórico (Último Ano)"] = ranking_df["PIB Histórico (Último Ano)"].map(
                lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")

            # Exibir a tabela de ranking (sem ISO_Alpha3 se não for relevante para o utilizador aqui)
            st.dataframe(ranking_df.drop(columns=[ColNames.ISO_ALPHA3], errors='ignore').set_index(ColNames.ENTITY),
                         use_container_width=True)

            st.subheader(f"Top e Bottom Países por CAGR Previsto (até {FORECAST_END_YEAR})")
            n_countries_cagr = st.slider("Número de países para ranking CAGR:", 5, 20, 10, key="cagr_slider")

            cagr_plot_df = pd.DataFrame(ranking_data_list)  # cagr_plot_df agora terá ISO_ALPHA3
            cagr_plot_df = cagr_plot_df.dropna(subset=[ColNames.CAGR])
            # Filtrar para não incluir agregados OWID ou N/A no plot de CAGR de países
            cagr_plot_df = cagr_plot_df[~cagr_plot_df[ColNames.ISO_ALPHA3].str.startswith('OWID_', na=False)]
            cagr_plot_df = cagr_plot_df[cagr_plot_df[ColNames.ISO_ALPHA3] != 'N/A']

            if not cagr_plot_df.empty:
                cagr_plot_df[ColNames.CAGR] = pd.to_numeric(cagr_plot_df[ColNames.CAGR], errors='coerce')
                cagr_plot_df_sorted = cagr_plot_df.sort_values(by=ColNames.CAGR, ascending=False)

                col_top_cagr, col_bottom_cagr = st.columns(2)
                with col_top_cagr:
                    top_n_cagr = cagr_plot_df_sorted.head(n_countries_cagr)
                    fig_bar_top_cagr = px.bar(top_n_cagr, x=ColNames.CAGR, y=ColNames.ENTITY, orientation='h',
                                              title=f"Top {n_countries_cagr} por CAGR")
                    fig_bar_top_cagr.update_layout(yaxis={'categoryorder': 'total ascending'}, xaxis_title="CAGR (%)")
                    st.plotly_chart(fig_bar_top_cagr, use_container_width=True)

                with col_bottom_cagr:
                    bottom_n_cagr = cagr_plot_df_sorted.tail(n_countries_cagr).sort_values(by=ColNames.CAGR,
                                                                                           ascending=True)
                    fig_bar_bottom_cagr = px.bar(bottom_n_cagr, x=ColNames.CAGR, y=ColNames.ENTITY, orientation='h',
                                                 title=f"Bottom {n_countries_cagr} por CAGR")
                    fig_bar_bottom_cagr.update_layout(yaxis={'categoryorder': 'total descending'},
                                                      xaxis_title="CAGR (%)")
                    st.plotly_chart(fig_bar_bottom_cagr, use_container_width=True)
            else:
                st.warning(
                    "Não há dados de CAGR suficientes para os rankings com os filtros atuais (após excluir agregados e N/A ISO).")
        else:
            st.warning("Não foi possível gerar a tabela de ranking.")
    else:
        st.warning("Dados filtrados vazios ou coluna CAGR não encontrada para a tabela de ranking.")

with tab3:
    st.subheader(f"Mapa Global do PIB per Capita Previsto")
    if selected_year_global and not filtered_df_by_continent.empty:
        df_map_data = filtered_df_by_continent[
            (filtered_df_by_continent[ColNames.YEAR] == selected_year_global) &
            (filtered_df_by_continent[ColNames.TYPE] == 'Forecast') &
            (filtered_df_by_continent[ColNames.ISO_ALPHA3] != 'N/A') &
            (~filtered_df_by_continent[ColNames.ISO_ALPHA3].str.startswith('OWID_', na=False))
            ]

        if not df_map_data.empty:
            try:
                fig_map = px.choropleth(
                    df_map_data,
                    locations=ColNames.ISO_ALPHA3,
                    color=ColNames.GDP_PER_CAPITA,
                    hover_name=ColNames.ENTITY,
                    color_continuous_scale=px.colors.sequential.Viridis,
                    title=f"PIB per Capita Previsto Globalmente - {selected_year_global}",
                    labels={ColNames.GDP_PER_CAPITA: 'PIB per Capita (USD)'},
                    projection="natural earth"
                )
                fig_map.update_layout(margin={"r": 0, "t": 30, "l": 0, "b": 0}, geo=dict(showcountries=True))
                st.plotly_chart(fig_map, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao gerar o mapa: {e}. Verifique os códigos ISO e os dados.")
        else:
            st.warning(
                f"Não há dados de previsão válidos para o mapa no ano {selected_year_global} com os filtros aplicados.")
    elif not selected_year_global:
        st.warning("Por favor, selecione um ano na barra lateral para a visualização global.")
    else:
        st.warning("Não há dados disponíveis para os filtros selecionados para o mapa.")

with tab4:
    st.subheader("Sobre o Modelo e Confiabilidade")
    st.markdown(f"""
    As previsões apresentadas foram geradas utilizando um modelo de Redes Neurais Recorrentes do tipo LSTM (Long Short-Term Memory) implementado em Keras (TensorFlow).
    O modelo foi otimizado com Optuna e treinado com dados históricos de PIB per capita e outras variáveis macroeconômicas relevantes até o último ano histórico disponível (aproximadamente **{LAST_HISTORICAL_YEAR_OVERALL}**).

    **Métricas de Performance do Modelo LSTM Keras (no conjunto de teste):**
    - **Erro Médio Absoluto (MAE):** ${MODEL_MAE:,.2f} USD
      - *Em média, as previsões do modelo no conjunto de teste desviaram este valor do PIB per capita real.*
    - **Erro Quadrático Médio (MSE):** {MODEL_MSE:,.0f}
      - *Esta métrica penaliza erros maiores de forma mais significativa.*
    - **Coeficiente de Determinação (R²):** {MODEL_R2:.4f}
      - *Aproximadamente **{(MODEL_R2 * 100):.2f}%** da variação no PIB per capita é explicada pelo modelo nos dados de teste, indicando um excelente ajuste.*

    **Considerações Importantes:**
    - As projeções até **{FORECAST_END_YEAR}** são baseadas na capacidade do modelo de aprender padrões históricos e na extrapolação simplificada das features exógenas. Elas carregam um grau de incerteza inerente a previsões de médio/longo prazo e devem ser interpretadas com cautela.
    - Eventos imprevistos (e.g., crises econômicas globais, pandemias, conflitos) podem impactar significativamente as trajetórias reais do PIB per capita de formas que o modelo não poderia antecipar com base nos dados históricos.
    - A performance do modelo pode variar entre diferentes países devido a características socioeconômicas únicas, qualidade e disponibilidade de dados históricos, e a ocorrência de choques específicos.
    """)
    st.markdown("""
    ---
    **Análise da Feature Dominante nos Modelos de Árvore (RandomForest/GradientBoosting):**
    Nos modelos de benchmark baseados em árvores (RandomForest e GradientBoosting), a feature `GDP_per_capita_lag1_orig_winsorized` (PIB per capita do ano anterior) demonstrou uma importância extremamente alta (frequentemente >0.90).
    * **Implicações:**
        * Isto reflete a forte autocorrelação do PIB per capita.
        * Pode mascarar a influência de outras features nestes modelos específicos.
        * Um baseline simples (PIB do ano anterior) seria muito competitivo para estes modelos.
    * **Diferença para o LSTM:** O modelo LSTM processa informações de lag de forma sequencial e integrada com outras features, explicando potencialmente o seu desempenho superior em R² ao capturar dinâmicas mais complexas.
    ---
    """)

# --- Rodapé ---
st.sidebar.markdown("---")
st.sidebar.markdown("#### Projeto de Data Science - Previsão de PIB per Capita")
st.sidebar.markdown("Desenvolvido por: [Seu Nome/Equipa]")
st.sidebar.markdown("Links:")
st.sidebar.markdown("- [Repositório GitHub](URL_DO_SEU_REPOSITORIO_AQUI)")
st.sidebar.markdown("- [Perfil LinkedIn](URL_DO_SEU_LINKEDIN_AQUI)")