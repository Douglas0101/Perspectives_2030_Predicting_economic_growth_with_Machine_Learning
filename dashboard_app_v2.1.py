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


# Configuração do Logger (opcional, para debug do dashboard)
# logger = logging.getLogger("dashboard_app")
# logger.setLevel(logging.DEBUG) # Mude para INFO para menos verbosidade
# if not logger.handlers:
#     ch = logging.StreamHandler()
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     ch.setFormatter(formatter)
#     logger.addHandler(ch)
# logger.propagate = False

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
    if not os.path.exists(file_path):
        st.error(f"ERRO CRÍTICO: O ficheiro de dados '{file_path}' não foi encontrado. "
                 f"Por favor, execute o script de preparação de dados ('prepare_dashboard_data.py') primeiro.")
        return pd.DataFrame()  # Retorna DataFrame vazio para evitar mais erros
    try:
        df = pd.read_csv(file_path)
        # logger.info(f"Dados carregados de {file_path} com shape: {df.shape}")

        # Garantir tipos corretos e tratar erros de conversão
        df[ColNames.YEAR] = pd.to_numeric(df[ColNames.YEAR], errors='coerce')
        df[ColNames.GDP_PER_CAPITA] = pd.to_numeric(df[ColNames.GDP_PER_CAPITA], errors='coerce')
        df[ColNames.CAGR] = pd.to_numeric(df[ColNames.CAGR], errors='coerce')

        # Remover linhas onde valores essenciais são NaN após conversão
        df.dropna(subset=[ColNames.YEAR, ColNames.GDP_PER_CAPITA], inplace=True)

        df[ColNames.ENTITY] = df[ColNames.ENTITY].astype(str)
        df[ColNames.TYPE] = df[ColNames.TYPE].astype(str)
        df[ColNames.ISO_ALPHA3] = df[ColNames.ISO_ALPHA3].fillna('N/A')
        df[ColNames.CONTINENT] = df[ColNames.CONTINENT].fillna('Desconhecido/Agregado')

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados do ficheiro '{file_path}': {e}")
        return pd.DataFrame()


# --- Carregamento dos Dados ---
DATA_FILE_PATH = os.path.join('data', 'gdp_dashboard_ready_data.csv')
df_dashboard = load_data(DATA_FILE_PATH)

# --- Métricas do Modelo (Valores da sua última execução completa) ---
# Estes valores devem ser atualizados com os da sua execução final mais recente e bem-sucedida.
# Com base no log de 2025-05-27 00:28:03 (que usou o cache correto de features):
MODEL_MAE = 178.14
MODEL_MSE = 937336.69
MODEL_R2 = 0.9885

if not df_dashboard.empty and ColNames.YEAR in df_dashboard.columns and not df_dashboard[
    df_dashboard[ColNames.TYPE] == 'Historical'].empty:
    LAST_HISTORICAL_YEAR_OVERALL = int(df_dashboard[df_dashboard[ColNames.TYPE] == 'Historical'][ColNames.YEAR].max())
else:
    LAST_HISTORICAL_YEAR_OVERALL = "N/A"  # Fallback se não houver dados históricos
FORECAST_END_YEAR = 2030

# --- Painel Lateral Esquerdo ("Configurações de Análise") ---
st.sidebar.image("https://i.imgur.com/GkzB5tD.png", width=100,
                 caption="Análise Econômica Global")  # Substitua pela URL da sua logo
st.sidebar.title("Painel de Controle")

# Filtro de Continente
all_continents_option = "Todos os Continentes"
# Inicializar filtered_df_by_continent com todos os dados para evitar NameError se df_dashboard estiver vazio
filtered_df_by_continent = df_dashboard.copy()

if not df_dashboard.empty and ColNames.CONTINENT in df_dashboard.columns:
    continent_options = sorted([c for c in df_dashboard[ColNames.CONTINENT].unique() if
                                c not in ['World', 'Desconhecido/Agregado'] and pd.notna(c)])
    select_box_options_continent = [all_continents_option] + continent_options

    selected_continent = st.sidebar.selectbox(
        "Selecione o Continente:",
        options=select_box_options_continent,
        index=0
    )
    if selected_continent != all_continents_option:
        filtered_df_by_continent = df_dashboard[df_dashboard[ColNames.CONTINENT] == selected_continent].copy()
    # else: filtered_df_by_continent já é df_dashboard.copy()
else:
    st.sidebar.warning("Coluna de Continente não encontrada ou dados vazios.")

# Seletor de Ano Final da Visualização (para o mapa e rankings)
selected_year_global = FORECAST_END_YEAR  # Default
if not filtered_df_by_continent.empty and ColNames.YEAR in filtered_df_by_continent.columns:
    # Usar anos de previsão do DataFrame filtrado por continente, se houver dados
    forecast_years_options = sorted(filtered_df_by_continent[filtered_df_by_continent[ColNames.TYPE] == 'Forecast'][
                                        ColNames.YEAR].unique().tolist())
    if not forecast_years_options and not df_dashboard.empty:  # Fallback para todos os dados se o filtro resultar em nada
        forecast_years_options = sorted(
            df_dashboard[df_dashboard[ColNames.TYPE] == 'Forecast'][ColNames.YEAR].unique().tolist())

    if forecast_years_options:
        # Tentar encontrar FORECAST_END_YEAR nas opções, senão usar o último disponível
        default_year_index_global = forecast_years_options.index(
            FORECAST_END_YEAR) if FORECAST_END_YEAR in forecast_years_options else (
            len(forecast_years_options) - 1 if forecast_years_options else 0)
        selected_year_global = st.sidebar.selectbox(
            "Selecione o Ano para Visão Global:",
            options=forecast_years_options,
            index=default_year_index_global
        )
    else:
        # selected_year_global permanece FORECAST_END_YEAR (default) ou pode ser None
        st.sidebar.warning("Não há anos de previsão disponíveis com os filtros atuais para seleção.")
else:
    st.sidebar.warning("Dados de dashboard vazios ou coluna 'Year' não encontrada.")

# (Opcional) Seletor de Comparação de Modelos - Placeholder para futura implementação
# st.sidebar.subheader("Comparação de Modelos (Opcional)")
# model_to_compare = st.sidebar.selectbox("Visualizar previsões de:", ["LSTM (Principal)", "RandomForest", "GradientBoosting"])
# if model_to_compare != "LSTM (Principal)":
#     st.sidebar.warning(f"Visualização comparativa para {model_to_compare} ainda não implementada.")

# (Desafio Criativo) Visualização de Incerteza/Erro - Placeholder
# st.sidebar.subheader("Visualização de Incerteza")
# show_uncertainty = st.sidebar.checkbox("Mostrar 'Faixa de Incerteza' (baseada no MAE)")


if st.sidebar.button("Resetar Filtros"):
    # A forma mais simples de resetar no Streamlit é limpar o session_state se estiver a usá-lo,
    # ou simplesmente forçar um rerun, o que re-executará o script com os valores default dos widgets.
    st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.info(f"""
**Projeto de Data Science**
- Modelo: LSTM Keras (R²: {MODEL_R2:.4f})
- Previsões até: {FORECAST_END_YEAR}
""")
st.sidebar.markdown("---")
st.sidebar.markdown("**Desenvolvido por:** [Seu Nome Aqui]")  # Substitua
st.sidebar.markdown("[Repositório GitHub](https://github.com/seu_usuario/seu_repo)")  # Substitua
st.sidebar.markdown("[Perfil LinkedIn](https://linkedin.com/in/seu_perfil)")  # Substitua

# --- Layout da Aplicação ---
st.title("🌍 Dashboard de Previsão do PIB per Capita Global")
st.markdown(f"""
Este dashboard apresenta uma análise do Produto Interno Bruto (PIB) per capita histórico e projeções até **{FORECAST_END_YEAR}**.
Utilize os filtros na barra lateral e as visualizações interativas para explorar as tendências econômicas globais e regionais.
As previsões são baseadas num modelo LSTM (Long Short-Term Memory) otimizado.
""")

# Seção de KPIs
st.header("Visão Geral e Performance do Modelo 📊")
if not df_dashboard.empty:
    num_entities_total = filtered_df_by_continent[ColNames.ENTITY].nunique()  # Contar entidades no df filtrado
    num_countries_with_iso = filtered_df_by_continent[
        (filtered_df_by_continent[ColNames.ISO_ALPHA3] != 'N/A') &
        (~filtered_df_by_continent[ColNames.ISO_ALPHA3].str.startswith('OWID_', na=False))
        ][ColNames.ENTITY].nunique()
else:
    num_entities_total = 0
    num_countries_with_iso = 0

kpi_cols = st.columns(4)
kpi_cols[0].metric("Entidades Selecionadas", f"{num_entities_total}")
kpi_cols[1].metric("Previsões Geradas Até", str(FORECAST_END_YEAR))
kpi_cols[2].metric("MAE do Modelo (Teste)", f"${MODEL_MAE:,.2f}")
kpi_cols[3].metric("R² do Modelo (Teste)", f"{MODEL_R2:.4f}")
if selected_continent != all_continents_option:
    st.caption(f"*Métricas do modelo são globais. Análise atual filtrada para {selected_continent}.*")
else:
    st.caption(
        f"*Análise inclui aproximadamente {num_countries_with_iso} países individuais com código ISO para visualizações de mapa.*")

# --- Abas para diferentes seções do dashboard ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["Séries Temporais por Entidade", "Rankings e CAGR", "Visão Global (Mapa)", "Sobre o Modelo"])

# Aba 1: Previsão Detalhada por Entidade
with tab1:
    st.subheader("Série Temporal: PIB per Capita (Histórico e Previsão)")
    if not filtered_df_by_continent.empty:
        entities_options_tab1 = sorted([
            e for e in filtered_df_by_continent[ColNames.ENTITY].unique()
            if e not in ['World'] and not e.endswith("(MPD)")  # Tentar excluir agregados por padrão
        ])
        if not entities_options_tab1 and not filtered_df_by_continent.empty:  # Fallback se só houver agregados
            entities_options_tab1 = sorted(filtered_df_by_continent[ColNames.ENTITY].unique().tolist())

        default_entities_tab1 = entities_options_tab1[:1] if entities_options_tab1 else []

        selected_entities_line = st.multiselect(
            "Selecione até 5 Países/Entidades para visualizar a série temporal:",
            options=entities_options_tab1,
            default=default_entities_tab1,
            max_selections=5,
            key="line_chart_entities"
        )

        if selected_entities_line:
            df_line_chart = filtered_df_by_continent[
                filtered_df_by_continent[ColNames.ENTITY].isin(selected_entities_line)]

            # Adicionar "Faixa de Incerteza" baseada no MAE (explicar claramente)
            if 'show_uncertainty_sidebar' in st.session_state and st.session_state.show_uncertainty_sidebar and ColNames.TYPE in df_line_chart.columns:
                df_line_chart['Upper_Bound_MAE'] = df_line_chart.apply(
                    lambda row: row[ColNames.GDP_PER_CAPITA] + MODEL_MAE if row[ColNames.TYPE] == 'Forecast' else row[
                        ColNames.GDP_PER_CAPITA], axis=1)
                df_line_chart['Lower_Bound_MAE'] = df_line_chart.apply(
                    lambda row: row[ColNames.GDP_PER_CAPITA] - MODEL_MAE if row[ColNames.TYPE] == 'Forecast' else row[
                        ColNames.GDP_PER_CAPITA], axis=1)

            fig_line = px.line(
                df_line_chart, x=ColNames.YEAR, y=ColNames.GDP_PER_CAPITA, color=ColNames.ENTITY,
                line_dash=ColNames.TYPE,
                title=f"PIB per Capita: Histórico e Previsão para {', '.join(selected_entities_line)}",
                labels={ColNames.GDP_PER_CAPITA: "PIB per Capita (USD)", ColNames.YEAR: "Ano"}, markers=True
            )
            # Adicionar faixas de incerteza se existirem
            if 'Upper_Bound_MAE' in df_line_chart.columns:
                for entity in selected_entities_line:
                    entity_data = df_line_chart[df_line_chart[ColNames.ENTITY] == entity]
                    fig_line.add_traces(
                        px.area(entity_data, x=ColNames.YEAR, y0='Lower_Bound_MAE', y1='Upper_Bound_MAE').data)

            fig_line.update_layout(legend_title_text='Entidade/Tipo')
            st.plotly_chart(fig_line, use_container_width=True)
            if 'show_uncertainty_sidebar' in st.session_state and st.session_state.show_uncertainty_sidebar:
                st.caption(
                    f"Nota: A 'faixa de incerteza' sombreada para previsões é ilustrativa, baseada no MAE global do modelo (${MODEL_MAE:,.2f}) e não representa um intervalo de confiança estatístico.")
        elif entities_options_tab1:
            st.info("Por favor, selecione pelo menos uma entidade para visualizar a série temporal.")
        else:
            st.warning("Não há entidades disponíveis para os filtros de continente selecionados.")
    else:
        st.warning("Não há dados disponíveis para os filtros globais selecionados.")

# Aba 2: Panorama Global e Rankings Comparativos
with tab2:
    st.subheader(f"Ranking de Entidades e CAGR Previsto (Último Ano Histórico até {FORECAST_END_YEAR})")
    if not filtered_df_by_continent.empty and ColNames.CAGR in filtered_df_by_continent.columns:
        ranking_data_list = []
        for entity, group in filtered_df_by_continent.groupby(ColNames.ENTITY):
            hist_data = group[group[ColNames.TYPE] == 'Historical']
            forecast_data_end_year = group[(group[ColNames.TYPE] == 'Forecast') & (
                        group[ColNames.YEAR] == selected_year_global)]  # Usar selected_year_global

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
                ColNames.ENTITY: entity, ColNames.CONTINENT: group[ColNames.CONTINENT].iloc[0],
                'Último Ano Histórico': int(last_hist_year_val) if pd.notna(last_hist_year_val) else 'N/A',
                'PIB Histórico (Último Ano)': last_hist_gdp_val,
                f"PIB Previsto ({selected_year_global})": forecast_gdp_val,  # Usar selected_year_global
                ColNames.CAGR: cagr_val, ColNames.ISO_ALPHA3: iso_alpha3_val
            })

        if ranking_data_list:
            ranking_df_display = pd.DataFrame(ranking_data_list)
            if ColNames.CAGR in ranking_df_display.columns:
                ranking_df_display[ColNames.CAGR] = pd.to_numeric(ranking_df_display[ColNames.CAGR], errors='coerce')

            # Permitir ordenação na tabela
            sort_by_col = st.selectbox("Ordenar tabela por:", options=ranking_df_display.columns.tolist(),
                                       index=ranking_df_display.columns.tolist().index(
                                           ColNames.CAGR) if ColNames.CAGR in ranking_df_display.columns else 0)
            ascending_order = st.checkbox("Ordem Ascendente", False)
            ranking_df_display = ranking_df_display.sort_values(by=sort_by_col, ascending=ascending_order).reset_index(
                drop=True)

            ranking_df_formatted = ranking_df_display.copy()
            ranking_df_formatted[ColNames.CAGR] = ranking_df_formatted[ColNames.CAGR].map(
                lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
            ranking_df_formatted[f"PIB Previsto ({selected_year_global})"] = ranking_df_formatted[
                f"PIB Previsto ({selected_year_global})"].map(lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")
            ranking_df_formatted["PIB Histórico (Último Ano)"] = ranking_df_formatted["PIB Histórico (Último Ano)"].map(
                lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")

            st.dataframe(
                ranking_df_formatted.drop(columns=[ColNames.ISO_ALPHA3], errors='ignore').set_index(ColNames.ENTITY),
                use_container_width=True, height=400)

            st.subheader(f"Top e Bottom Países por CAGR Previsto (Histórico até {selected_year_global})")
            n_countries_cagr = st.slider("Número de países para ranking CAGR:", min_value=3, max_value=20, value=10,
                                         key="cagr_slider_tab2")

            cagr_plot_df = ranking_df_display.copy()
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
                                                                                           ascending=True)
                    fig_bar_bottom_cagr = px.bar(bottom_n_cagr, x=ColNames.CAGR, y=ColNames.ENTITY, orientation='h',
                                                 title=f"Bottom {n_countries_cagr} por CAGR")
                    fig_bar_bottom_cagr.update_layout(yaxis={'categoryorder': 'total descending'},
                                                      xaxis_title="CAGR (%)")
                    st.plotly_chart(fig_bar_bottom_cagr, use_container_width=True)
            else:
                st.warning("Não há dados de CAGR suficientes para os rankings de Top/Bottom com os filtros atuais.")
        else:
            st.warning("Não foi possível gerar dados para a tabela de ranking.")
    else:
        st.warning("Dados filtrados vazios ou coluna CAGR não encontrada para a tabela de ranking.")

# Aba 3: Visão Global (Mapa)
with tab3:
    st.subheader(f"Mapa Global do PIB per Capita Previsto")
    if selected_year_global and not filtered_df_by_continent.empty:  # Usar filtered_df_by_continent aqui também
        df_map_data = filtered_df_by_continent[
            (filtered_df_by_continent[ColNames.YEAR] == selected_year_global) &
            (filtered_df_by_continent[ColNames.TYPE] == 'Forecast') &
            (filtered_df_by_continent[ColNames.ISO_ALPHA3] != 'N/A') &
            (~filtered_df_by_continent[ColNames.ISO_ALPHA3].str.startswith('OWID_', na=False))
            ]

        if not df_map_data.empty:
            try:
                # Escolher uma métrica para o mapa
                map_metric_options = [ColNames.GDP_PER_CAPITA, ColNames.CAGR]
                map_metric_selected = st.selectbox("Métrica para exibir no mapa:", map_metric_options,
                                                   format_func=lambda
                                                       x: "PIB per Capita Previsto" if x == ColNames.GDP_PER_CAPITA else "CAGR Previsto")

                fig_map = px.choropleth(
                    df_map_data,
                    locations=ColNames.ISO_ALPHA3,
                    color=map_metric_selected,
                    hover_name=ColNames.ENTITY,
                    hover_data={ColNames.GDP_PER_CAPITA: ':.2f', ColNames.CAGR: ':.2f', ColNames.CONTINENT: True},
                    color_continuous_scale=px.colors.sequential.Plasma if map_metric_selected == ColNames.GDP_PER_CAPITA else px.colors.diverging.RdYlGn,
                    title=f"{'PIB per Capita Previsto' if map_metric_selected == ColNames.GDP_PER_CAPITA else 'CAGR Previsto'} Globalmente - {selected_year_global}",
                    labels={ColNames.GDP_PER_CAPITA: 'PIB per Capita (USD)', ColNames.CAGR: 'CAGR (%)'},
                    projection="natural earth"
                )
                fig_map.update_layout(margin={"r": 0, "t": 50, "l": 0, "b": 0},
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

# Aba 4: Sobre o Modelo
with tab4:
    st.subheader("Sobre o Modelo e Confiabilidade")
    # ... (Conteúdo mantido como antes, com a análise da feature dominante) ...
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
    # Adicionar aqui um placeholder para o gráfico de dispersão (Reais vs. Previstos) se desejar
    # st.subheader("Diagnóstico do Modelo: Reais vs. Previstos (Conjunto de Teste)")
    # if 'df_test_lstm_processed_global' e as previsões do teste estiverem disponíveis
    # (requereria carregar ou passar os resultados da avaliação do modelo)
    # fig_scatter = px.scatter(x=y_reais_teste, y=y_previstos_teste, labels={'x':'PIB Real', 'y':'PIB Previsto'}, title='Reais vs. Previstos (Teste)')
    # fig_scatter.add_shape(type="line", line=dict(dash='dash'), x0=y_reais_teste.min(), y0=y_reais_teste.min(), x1=y_reais_teste.max(), y1=y_reais_teste.max())
    # st.plotly_chart(fig_scatter, use_container_width=True)

# Mensagem final se os dados não puderem ser carregados
if df_dashboard.empty:
    st.error("Não foi possível carregar os dados para o dashboard. Verifique o caminho do ficheiro e os logs.")

# streamlit run dashboard_app_v2.1.py