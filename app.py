# Arquivo: app.py
import streamlit as st
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder

# --- CONSTANTES GLOBAIS ---
ROOT = Path(__file__).resolve().parent
FORECAST_YEAR = 2030

# ─── 1) CONFIGURAÇÃO DE PÁGINA E CSS ─────────────────────────────
st.set_page_config(
    page_title=f"🌐 Dashboard de Previsão do PIB per Capita {FORECAST_YEAR}",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_css(css_file):
    """Carrega um arquivo CSS e o injeta no app."""
    path = ROOT / css_file
    if path.exists():
        return path.read_text(encoding="utf-8")
    st.warning(f"Arquivo CSS '{css_file}' não encontrado.")
    return ""


st.markdown(f"<style>{load_css('assets/custom.css')}</style>", unsafe_allow_html=True)


# ─── 2) CONFIGURAÇÃO DO PLOTLY ────────────────────────────────────
def register_plotly_templates():
    """Define e registra templates customizados para Plotly."""
    import plotly.io as pio
    colorway = ['#00BCD4', '#E91E63', '#4CAF50', '#FFC107', '#FF5722', '#9C27B0']

    template_base = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff'), title_font=dict(color='#ffffff'),
            legend=dict(font=dict(color='#ffffff'), bgcolor='rgba(42,55,71,0.7)'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.3)',
                       tickfont=dict(color='#ffffff')),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.3)',
                       tickfont=dict(color='#ffffff')),
            colorway=colorway
        )
    )
    template_globe = go.layout.Template(layout=go.Layout(paper_bgcolor='rgba(0,0,0,0)'))

    pio.templates["custom_dark_base"] = template_base
    pio.templates["custom_dark_globe"] = template_globe
    pio.templates.default = "custom_dark_base"


register_plotly_templates()


# ─── 3) CARREGAMENTO DE DADOS (OTIMIZADO) ───────────────────────
@st.cache_data
def load_data(file_path):
    """Carrega dados pré-processados de um único arquivo Parquet."""
    path = ROOT / file_path
    if not path.exists():
        st.error(f"Arquivo de dados '{file_path}' não encontrado. Execute o script `preprocess_data.py` primeiro.")
        return None
    try:
        return pd.read_parquet(path)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Parquet '{path}': {e}")
        return None


# ─── 4) FUNÇÕES DE GERAÇÃO DE GRÁFICOS E COMPONENTES ──────────────
def create_plotly_globe_map(df_map: pd.DataFrame):
    """Cria e retorna uma figura de globo interativo do Plotly."""
    if df_map is None or df_map.empty or 'ISO_Alpha3' not in df_map.columns:
        return None

    df_plot = df_map.dropna(subset=['ISO_Alpha3', 'GDP_per_capita']).copy()
    if df_plot.empty:
        return None

    df_plot['GDP_log'] = np.log1p(df_plot['GDP_per_capita'])
    df_plot['CAGR_hover'] = df_plot['CAGR'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")

    fig = go.Figure(data=go.Choropleth(
        locations=df_plot['ISO_Alpha3'],
        z=df_plot['GDP_log'],
        customdata=df_plot[['Country', 'GDP_per_capita', 'CAGR_hover']],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br><br>"
            f"PIB per Capita ({FORECAST_YEAR}): $%{{customdata[1]:,.0f}}<br>"
            f"CAGR (até {FORECAST_YEAR}): %{{customdata[2]}}"
            "<extra></extra>"
        ),
        colorscale='Reds', marker_line_color='#d1d1d1', marker_line_width=0.5,
        colorbar_title='PIB per Capita (log)',
    ))
    fig.update_layout(
        geo=dict(
            showframe=False, showcoastlines=False, projection_type='orthographic',
            showcountries=True, countrycolor='#d1d1d1',
            showocean=True, oceancolor='#c9d2e0', bgcolor='rgba(0,0,0,0)'
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=600, template="custom_dark_globe"
    )
    return fig


def calculate_kpis(df: pd.DataFrame):
    """Calcula os KPIs (Key Performance Indicators) a partir do DataFrame de previsão."""
    if df is None or df.empty:
        return {"max_gdp": 0, "top_gdp_country": "N/A", "avg_gdp": 0, "top_cagr_country": "N/A", "max_cagr_val": 0}

    kpis = {}
    kpis["max_gdp"] = df["GDP_per_capita"].max()
    kpis["top_gdp_country"] = df.loc[df["GDP_per_capita"].idxmax()]["Country"] if not df.empty else "N/A"
    kpis["avg_gdp"] = df["GDP_per_capita"].mean()

    if "CAGR" in df.columns and df["CAGR"].notna().any():
        max_cagr_row = df.loc[df["CAGR"].idxmax()]
        kpis["top_cagr_country"] = max_cagr_row["Country"]
        kpis["max_cagr_val"] = max_cagr_row["CAGR"]
    else:
        kpis["top_cagr_country"] = "N/A"
        kpis["max_cagr_val"] = 0
    return kpis


def display_timeseries_tab(df_ts: pd.DataFrame, selected_continent: str):
    st.subheader("Série Temporal: Histórico vs. Previsão")
    df_plot = df_ts if selected_continent == "Todos" else df_ts[df_ts["Continent"] == selected_continent]

    if df_plot.empty:
        st.info(f"Nenhum dado de série temporal disponível para '{selected_continent}'.")
        return

    countries_available = sorted(df_plot["Country"].dropna().unique())
    if not countries_available:
        st.info(f"Nenhum país com dados disponíveis para '{selected_continent}'.")
        return

    sel_ct = st.multiselect(
        "Selecione até 5 países:", countries_available,
        default=countries_available[:min(5, len(countries_available))],
        max_selections=5, key="countries_timeseries"
    )

    if sel_ct:
        df_chart = df_plot[df_plot["Country"].isin(sel_ct)].sort_values(by=['Country', 'Type', 'Year'])
        fig = px.line(
            df_chart, x="Year", y="GDP_per_capita", color="Country", line_dash="Type", markers=True,
            labels={"GDP_per_capita": "PIB per Capita (USD)", "Year": "Ano", "Country": "País", "Type": "Tipo"}
        )
        fig.update_layout(yaxis_tickformat="$,.0f")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Selecione um ou mais países para visualizar o gráfico.")


def display_ranking_tab(df_fc: pd.DataFrame, selected_continent: str):
    st.subheader("Top/Bottom CAGR Previsto")
    df_rank = df_fc if selected_continent == "Todos" else df_fc[df_fc["Continent"] == selected_continent]
    df_rank = df_rank.dropna(subset=['CAGR'])

    if df_rank.empty:
        st.info("Não há dados de CAGR para exibir um ranking com os filtros atuais.")
        return

    n_countries = min(20, df_rank['Country'].nunique())
    n = st.slider(
        "Número de países para ranking:", min_value=1, max_value=n_countries,
        value=min(10, n_countries), key="ranking_slider"
    ) if n_countries > 1 else 1

    col_top, col_bot = st.columns(2)
    with col_top:
        st.markdown("##### Top Maiores Crescimentos (CAGR)")
        top_data = df_rank.nlargest(n, "CAGR").sort_values("CAGR", ascending=True)
        fig = px.bar(top_data, x="CAGR", y="Country", orientation="h", color="CAGR",
                     color_continuous_scale=px.colors.sequential.Viridis,
                     labels={"CAGR": "CAGR (%)", "Country": ""})
        fig.update_layout(xaxis_tickformat=".2%");
        st.plotly_chart(fig, use_container_width=True)
    with col_bot:
        st.markdown("##### Bottom Menores Crescimentos (CAGR)")
        bot_data = df_rank.nsmallest(n, "CAGR").sort_values("CAGR", ascending=False)
        fig = px.bar(bot_data, x="CAGR", y="Country", orientation="h", color="CAGR",
                     color_continuous_scale=px.colors.sequential.Plasma_r,
                     labels={"CAGR": "CAGR (%)", "Country": ""})
        fig.update_layout(xaxis_tickformat=".2%");
        st.plotly_chart(fig, use_container_width=True)


# ─── 5) FUNÇÃO PRINCIPAL (MAIN) ──────────────────────────────────
def main():
    df_full = load_data("data/dashboard_data.parquet")
    if df_full is None:
        st.stop()

    df_fc_2030 = df_full[(df_full['Type'] == 'Forecast') & (df_full['Year'] == FORECAST_YEAR)].copy()

    st.title(f"🌐 Dashboard de Previsão do PIB per Capita Global {FORECAST_YEAR}")
    st.write(f"Análise histórica e projeções interativas do PIB per capita até {FORECAST_YEAR}.")

    st.sidebar.header("Filtros Globais 🌍")
    continents = ["Todos"] + sorted(df_full["Continent"].dropna().unique())
    selected_continent = st.sidebar.selectbox("Selecione o Continente:", continents, key="sb_continent")

    df_filtered_fc = df_fc_2030 if selected_continent == "Todos" else df_fc_2030[
        df_fc_2030["Continent"] == selected_continent]

    st.sidebar.markdown("---")
    st.sidebar.info("Dashboard desenvolvido por Douglas Souza.")
    st.sidebar.markdown("[Repositório GitHub](#) • [Perfil LinkedIn](#)")

    kpis = calculate_kpis(df_filtered_fc)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Maior PIB/Cap ({FORECAST_YEAR})", f"${kpis['max_gdp']:,.0f}")
    c2.metric("País Top PIB", kpis['top_gdp_country'])
    c3.metric(f"Média PIB/Cap ({selected_continent})", f"${kpis['avg_gdp']:,.0f}")
    c4.metric("Maior CAGR", f"{kpis['top_cagr_country']} ({kpis['max_cagr_val']:.2%})")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["Série Temporal", "Ranking & CAGR", "Visão Global (Mapa)", "Sobre o Modelo"])
    with tab1:
        display_timeseries_tab(df_full, selected_continent)
    with tab2:
        display_ranking_tab(df_fc_2030, selected_continent)
    with tab3:
        st.subheader(f"Visão Global do PIB per Capita ({FORECAST_YEAR}) - Globo Interativo")
        fig_globe = create_plotly_globe_map(df_fc_2030)
        if fig_globe:
            st.plotly_chart(fig_globe, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning(
                "Não foi possível gerar o mapa globo. Verifique se os dados de previsão e os códigos ISO estão disponíveis.")
    with tab4:
        st.subheader("Sobre o Modelo e Confiabilidade")
        mae, r2, mse = 178.14, 0.9885, 937337
        st.markdown(f"- **Modelo:** LSTM (Keras), otimizado com Optuna.\n"
                    f"- **Métricas (Teste):** MAE: ${mae:,.2f}, R²: {r2:.4f}, MSE: {mse:,.2f}\n"
                    "> **Nota:** Projeções de longo prazo são inerentemente incertas e devem ser "
                    "interpretadas como tendências e não como valores exatos.")

    st.markdown("---")
    st.subheader(f"Dados Detalhados (Previsão {FORECAST_YEAR})")
    if not df_filtered_fc.empty:
        st.download_button(
            "📥 Exportar Seleção para CSV",
            df_filtered_fc.to_csv(index=False).encode("utf-8"),
            f"forecast_{FORECAST_YEAR}_{selected_continent.lower().replace(' ', '_')}.csv",
            "text/csv"
        )
        gb = GridOptionsBuilder.from_dataframe(df_filtered_fc)
        gb.configure_default_column(filter=True, sortable=True, resizable=True, groupable=True)
        gb.configure_column("GDP_per_capita", type=["numericColumn"],
                            valueFormatter="'$' + value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})")
        gb.configure_column("CAGR", type=["numericColumn"],
                            valueFormatter="value == null ? '' : (typeof value === 'number' ? (value * 100).toFixed(2) + '%' : '')")
        gridOptions = gb.build()
        AgGrid(df_filtered_fc, gridOptions=gridOptions, theme="streamlit-dark", fit_columns_on_grid_load=True,
               allow_unsafe_jscode=True)
    else:
        st.info("Sem dados detalhados para a seleção atual.")


if __name__ == "__main__":
    main()