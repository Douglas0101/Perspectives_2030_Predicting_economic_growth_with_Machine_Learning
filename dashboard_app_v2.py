import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import logging

# Configuração da página (deve ser a primeira chamada do Streamlit)
st.set_page_config(
    page_title="Dashboard de Previsão de PIB per Capita Global",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Configuração do Logger para o dashboard (opcional)
# dashboard_logger = logging.getLogger("gdp_dashboard_app")
# dashboard_logger.setLevel(logging.INFO)
# if not dashboard_logger.handlers:
#     ch = logging.StreamHandler()
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     ch.setFormatter(formatter)
#     dashboard_logger.addHandler(ch)
# dashboard_logger.propagate = False


# Constantes para nomes de colunas
class ColNames:
    ENTITY = 'Entity'
    YEAR = 'Year'
    GDP_PER_CAPITA = 'GDP_per_capita'
    TYPE = 'Type'
    ISO_ALPHA3 = 'ISO_Alpha3'
    CONTINENT = 'Continent'
    CAGR = 'CAGR_Forecast'


@st.cache_data  # Cache para otimizar o carregamento de dados
def load_data(file_path):
    """Carrega e pré-processa minimamente os dados para o dashboard."""
    try:
        df = pd.read_csv(file_path)
        # dashboard_logger.info(f"Dados carregados de {file_path} com shape: {df.shape}")

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
            f"ERRO: O ficheiro de dados '{file_path}' não foi encontrado. Certifique-se de que o script 'prepare_dashboard_data.py' foi executado e o ficheiro 'gdp_dashboard_ready_data.csv' está na pasta 'data'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados: {e}")
        return pd.DataFrame()


# --- Carregamento dos Dados ---
DATA_FILE_PATH = os.path.join('data', 'gdp_dashboard_ready_data.csv')
df_dashboard = load_data(DATA_FILE_PATH)

# --- Métricas do Modelo (Valores da sua última execução completa) ---
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
    # Excluir 'World' e 'Desconhecido/Agregado' das opções de filtro, mas permitir 'Todos'
    continent_options = sorted(
        [c for c in df_dashboard[ColNames.CONTINENT].unique() if c not in ['World', 'Desconhecido/Agregado']])

    # Adicionar a opção "Todos" no início
    select_box_options = [all_continents_option] + continent_options

    selected_continent = st.sidebar.selectbox(
        "Selecione o Continente:",
        options=select_box_options,
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
    if not forecast_years and not df_dashboard.empty:  # Fallback para todos os dados se o filtro resultar em nada
        forecast_years = sorted(
            df_dashboard[df_dashboard[ColNames.TYPE] == 'Forecast'][ColNames.YEAR].unique().tolist())

    default_year_index = forecast_years.index(FORECAST_END_YEAR) if FORECAST_END_YEAR in forecast_years else (
        len(forecast_years) - 1 if forecast_years else 0)

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

# --- Botão de Resetar Filtros (Funcionalidade Básica) ---
if st.sidebar.button("Resetar Filtros"):
    # Para resetar, teríamos que limpar o estado dos widgets.
    # No Streamlit, isso geralmente significa definir os valores padrão novamente ou usar session_state.
    # Para simplicidade aqui, esta é uma sugestão de local para o botão.
    # A lógica de reset pode ser mais complexa dependendo de como os filtros são armazenados.
    # Uma forma simples é forçar um rerun com valores default, mas o selectbox já faz isso se mudado.
    st.experimental_rerun()  # Força um rerun, que pode resetar alguns widgets para o padrão

st.sidebar.markdown("---")
st.sidebar.info("""
**Desenvolvido como parte de um Projeto de Data Science.**
- **Modelo Principal:** LSTM Keras (R²: {MODEL_R2:.4f})
- **Fonte de Dados:** PIB per capita histórico e projeções.
""".format(MODEL_R2=MODEL_R2))
st.sidebar.markdown("---")
st.sidebar.markdown("Adicione aqui links para seu GitHub/LinkedIn:")
st.sidebar.markdown("- [Seu Repositório GitHub](https://github.com/Douglas0101/Perspectives_2030_Predicting_economic_growth_with_Machine_Learning)")  # Substitua pela URL real
st.sidebar.markdown("- [Seu Perfil LinkedIn](https://www.linkedin.com/in/douglas-d-souza/)")  # Substitua pela URL real

# --- Layout da Aplicação ---
st.title("🌍 Dashboard de Previsão do PIB per Capita Global")
st.markdown(f"""
Este dashboard apresenta uma análise do Produto Interno Bruto (PIB) per capita histórico e projeções até **{FORECAST_END_YEAR}**.
Utilize os filtros na barra lateral e as visualizações interativas para explorar as tendências econômicas globais e regionais.
""")

# Seção de KPIs
st.header("Visão Geral e Performance do Modelo 📊")
if not df_dashboard.empty:
    num_entities_total = df_dashboard[ColNames.ENTITY].nunique()
    num_countries_with_iso = df_dashboard[
        (df_dashboard[ColNames.ISO_ALPHA3] != 'N/A') &
        (~df_dashboard[ColNames.ISO_ALPHA3].str.startswith('OWID_', na=False))
        ][ColNames.ENTITY].nunique()
else:
    num_entities_total = 0
    num_countries_with_iso = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Entidades (Países/Regiões)", f"{num_entities_total}")
col2.metric("Previsões Geradas Até", str(FORECAST_END_YEAR))
col3.metric("MAE Modelo LSTM (Teste)", f"${MODEL_MAE:,.2f}")
col4.metric("R² Modelo LSTM (Teste)", f"{MODEL_R2:.4f}")
st.caption(f"*Análise inclui {num_countries_with_iso} países individuais com código ISO para visualizações de mapa.*")

# --- Abas para diferentes seções do dashboard ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["Séries Temporais por Entidade", "Rankings e CAGR", "Visão Global (Mapa)", "Sobre o Modelo"])

with tab1:
    st.subheader("Série Temporal: PIB per Capita (Histórico e Previsão)")
    if not filtered_df_by_continent.empty:
        # Excluir agregados da lista de seleção principal para o gráfico de linhas
        entities_to_select_from = sorted([
            e for e in filtered_df_by_continent[ColNames.ENTITY].unique()
            if e not in ["World"] and not e.endswith("(MPD)")
        ])
        if not entities_to_select_from and not filtered_df_by_continent.empty:  # Se só houver agregados no filtro
            entities_to_select_from = sorted(filtered_df_by_continent[ColNames.ENTITY].unique().tolist())

        default_selection = entities_to_select_from[:1] if entities_to_select_from else []

        selected_entities_line = st.multiselect(
            "Selecione até 5 Países/Entidades para visualizar a série temporal:",
            options=entities_to_select_from,
            default=default_selection,
            max_selections=5
        )

        if selected_entities_line:
            df_line_chart = filtered_df_by_continent[
                filtered_df_by_continent[ColNames.ENTITY].isin(selected_entities_line)]

            fig_line = px.line(
                df_line_chart,
                x=ColNames.YEAR,
                y=ColNames.GDP_PER_CAPITA,
                color=ColNames.ENTITY,
                line_dash=ColNames.TYPE,
                title="PIB per Capita: Histórico vs. Previsão",
                labels={ColNames.GDP_PER_CAPITA: "PIB per Capita (USD)", ColNames.YEAR: "Ano"},
                markers=True
            )
            fig_line.update_layout(legend_title_text='Entidade/Tipo')
            st.plotly_chart(fig_line, use_container_width=True)
        elif entities_to_select_from:  # Se há opções mas nenhuma selecionada
            st.info("Por favor, selecione pelo menos uma entidade para visualizar a série temporal.")
        else:  # Se não há opções de entidade após os filtros
            st.warning("Não há entidades disponíveis para os filtros de continente selecionados.")
    else:
        st.warning("Não há dados disponíveis para os filtros globais selecionados.")

with tab2:
    st.subheader(f"Ranking de Entidades e CAGR Previsto (Último Ano Histórico até {FORECAST_END_YEAR})")
    if not filtered_df_by_continent.empty and ColNames.CAGR in filtered_df_by_continent.columns:
        # Preparar dados para a tabela de ranking
        ranking_data_list = []
        # Usar o df filtrado pelo continente para o ranking
        for entity, group in filtered_df_by_continent.groupby(ColNames.ENTITY):
            hist_data = group[group[ColNames.TYPE] == 'Historical']
            forecast_data_end_year = group[
                (group[ColNames.TYPE] == 'Forecast') & (group[ColNames.YEAR] == FORECAST_END_YEAR)]

            last_hist_year_val = hist_data[ColNames.YEAR].max() if not hist_data.empty else np.nan
            last_hist_gdp_val = hist_data[hist_data[ColNames.YEAR] == last_hist_year_val][ColNames.GDP_PER_CAPITA].iloc[
                0] if not hist_data.empty and pd.notna(last_hist_year_val) and not \
            hist_data[hist_data[ColNames.YEAR] == last_hist_year_val][ColNames.GDP_PER_CAPITA].empty else np.nan

            forecast_gdp_val = forecast_data_end_year[ColNames.GDP_PER_CAPITA].iloc[
                0] if not forecast_data_end_year.empty else np.nan

            cagr_val = group[ColNames.CAGR].iloc[0] if ColNames.CAGR in group.columns and not group[
                ColNames.CAGR].empty and pd.notna(group[ColNames.CAGR].iloc[0]) else np.nan
            iso_alpha3_val = group[ColNames.ISO_ALPHA3].iloc[0] if ColNames.ISO_ALPHA3 in group.columns and not group[
                ColNames.ISO_ALPHA3].empty else 'N/A'

            ranking_data_list.append({
                ColNames.ENTITY: entity,
                'Último Ano Histórico': int(last_hist_year_val) if pd.notna(last_hist_year_val) else 'N/A',
                'PIB Histórico (Último Ano)': last_hist_gdp_val,
                f"PIB Previsto ({FORECAST_END_YEAR})": forecast_gdp_val,
                ColNames.CAGR: cagr_val,
                ColNames.ISO_ALPHA3: iso_alpha3_val
            })

        if ranking_data_list:
            ranking_df_display = pd.DataFrame(ranking_data_list)
            # Ordenar por CAGR descendente por padrão, se a coluna existir e for numérica
            if ColNames.CAGR in ranking_df_display.columns:
                ranking_df_display[ColNames.CAGR] = pd.to_numeric(ranking_df_display[ColNames.CAGR], errors='coerce')
                ranking_df_display = ranking_df_display.sort_values(by=ColNames.CAGR, ascending=False)

            # Formatação para exibição
            ranking_df_formatted = ranking_df_display.copy()
            ranking_df_formatted[ColNames.CAGR] = ranking_df_formatted[ColNames.CAGR].map(
                lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
            ranking_df_formatted[f"PIB Previsto ({FORECAST_END_YEAR})"] = ranking_df_formatted[
                f"PIB Previsto ({FORECAST_END_YEAR})"].map(lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")
            ranking_df_formatted["PIB Histórico (Último Ano)"] = ranking_df_formatted["PIB Histórico (Último Ano)"].map(
                lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")

            st.dataframe(
                ranking_df_formatted.drop(columns=[ColNames.ISO_ALPHA3], errors='ignore').set_index(ColNames.ENTITY),
                use_container_width=True)

            st.subheader(f"Top e Bottom Países por CAGR Previsto (até {FORECAST_END_YEAR})")
            n_countries_cagr = st.slider("Número de países para ranking CAGR:", min_value=3, max_value=20, value=10,
                                         key="cagr_slider")

            cagr_plot_df = ranking_df_display.copy()  # Usar o df com CAGR numérico
            cagr_plot_df = cagr_plot_df.dropna(subset=[ColNames.CAGR])
            cagr_plot_df = cagr_plot_df[cagr_plot_df[ColNames.ISO_ALPHA3] != 'N/A']
            cagr_plot_df = cagr_plot_df[~cagr_plot_df[ColNames.ISO_ALPHA3].str.startswith('OWID_', na=False)]

            if not cagr_plot_df.empty:
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
                                                                                           ascending=True)  # Ordenar corretamente para bottom
                    fig_bar_bottom_cagr = px.bar(bottom_n_cagr, x=ColNames.CAGR, y=ColNames.ENTITY, orientation='h',
                                                 title=f"Bottom {n_countries_cagr} por CAGR")
                    fig_bar_bottom_cagr.update_layout(yaxis={'categoryorder': 'total descending'},
                                                      xaxis_title="CAGR (%)")  # Ordem invertida
                    st.plotly_chart(fig_bar_bottom_cagr, use_container_width=True)
            else:
                st.warning("Não há dados de CAGR suficientes para os rankings de Top/Bottom com os filtros atuais.")
        else:
            st.warning("Não foi possível gerar dados para a tabela de ranking.")
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
                fig_map.update_layout(margin={"r": 0, "t": 30, "l": 0, "b": 0},
                                      geo=dict(showcountries=True, landcolor='lightgray', oceancolor='lightblue'))
                st.plotly_chart(fig_map, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao gerar o mapa: {e}. Verifique os códigos ISO e os dados.")
        else:
            st.warning(
                f"Não há dados de previsão válidos para o mapa no ano {selected_year_global} com os filtros aplicados (verifique se há códigos ISO válidos).")
    elif not selected_year_global:
        st.warning("Por favor, selecione um ano na barra lateral para a visualização global.")
    else:
        st.warning("Não há dados disponíveis para os filtros globais selecionados para o mapa.")

with tab4:
    st.subheader("Sobre o Modelo e Confiabilidade")
    st.markdown(f"""
    As previsões apresentadas foram geradas utilizando um modelo de Redes Neurais Recorrentes do tipo LSTM (Long Short-Term Memory) implementado em Keras (TensorFlow).
    O modelo foi otimizado com Optuna e treinado com dados históricos de PIB per capita e outras variáveis macroeconômicas relevantes até o último ano histórico disponível (aproximadamente **{int(LAST_HISTORICAL_YEAR_OVERALL) if pd.notna(LAST_HISTORICAL_YEAR_OVERALL) else 'N/A'}**).

    **Métricas de Performance do Modelo LSTM Keras (no conjunto de teste completo):**
    - **Erro Médio Absoluto (MAE):** ${MODEL_MAE:,.2f} USD
      - *Em média, as previsões do modelo no conjunto de teste desviaram este valor do PIB per capita real.*
    - **Erro Quadrático Médio (MSE):** {MODEL_MSE:,.0f}
      - *Esta métrica penaliza erros maiores de forma mais significativa.*
    - **Coeficiente de Determinação (R²):** {MODEL_R2:.4f}
      - *Aproximadamente **{(MODEL_R2 * 100):.2f}%** da variação no PIB per capita é explicada pelo modelo nos dados de teste, indicando um excelente ajuste.*

    **Considerações Importantes:**
    - As projeções até **{FORECAST_END_YEAR}** são baseadas na capacidade do modelo de aprender padrões históricos e na extrapolação simplificada das features exógenas (utilizando uma tendência linear dos últimos 5 anos ou o último valor conhecido). Elas carregam um grau de incerteza inerente a previsões de médio/longo prazo e devem ser interpretadas com cautela.
    - Eventos imprevistos (e.g., crises econômicas globais, pandemias, conflitos, mudanças políticas drásticas) podem impactar significativamente as trajetórias reais do PIB per capita de formas que o modelo não poderia antecipar com base nos dados históricos.
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