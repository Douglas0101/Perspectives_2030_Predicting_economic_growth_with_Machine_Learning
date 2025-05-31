import streamlit as st
from pathlib import Path
import pandas as pd
import geopandas
import matplotlib.pyplot as plt  # Mantido caso alguma função estática ainda seja usada ou para referência
import plotly.graph_objects as go
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode
import time

# ─── 1) CONFIGURAÇÃO DE PÁGINA ─────────────────────────────────
st.set_page_config(
    page_title="🌐 Dashboard de Previsão do PIB per Capita 2030",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 2) INJEÇÃO DO CSS CUSTOMIZADO ──────────────────────────────
ROOT = Path(__file__).resolve().parent
css_path = ROOT / "assets" / "custom.css"
if css_path.exists():
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
else:
    st.warning("Arquivo custom.css não encontrado.")


# ─── 3) TEMPLATE PLOTLY ESCURO + PALETA  ─────────────────────────
def register_plotly_template():
    import plotly.io as pio
    import plotly.express as px
    colorway = ['#00BCD4', '#E91E63', '#4CAF50', '#FFC107', '#FF5722', '#9C27B0']
    pio.templates["custom_dark_base"] = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'),
            title_font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), bgcolor='rgba(42,55,71,0.7)'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.3)',
                       tickfont=dict(color='#ffffff')),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.3)',
                       tickfont=dict(color='#ffffff'))
        )
    )
    pio.templates["custom_dark_globe"] = go.layout.Template(
        layout=go.Layout(paper_bgcolor='rgba(0,0,0,0)')
    )
    pio.templates["custom_dark_base"].layout.colorway = colorway
    pio.templates.default = "custom_dark_base"


register_plotly_template()
import plotly.express as px


# ─── 4) CARREGAMENTO E PREPARO DE DADOS ─────────────────────────
@st.cache_data
def load_data():
    # load_start_time = time.time() # Comentado
    # st.sidebar.caption(f"Cache miss: Executando load_data()... {time.strftime('%H:%M:%S')}") # REMOVIDO
    dd = ROOT / "data"
    country_to_continent_map, country_to_cagr_map, country_to_iso_map = {}, {}, {}

    df_ready_path = dd / "gdp_dashboard_ready_data.csv"
    df_ready = pd.DataFrame()

    if df_ready_path.exists():
        df_ready = pd.read_csv(df_ready_path).rename(columns={"Entity": "Country"})
        if not df_ready.empty:
            if 'Country' in df_ready.columns and 'Continent' in df_ready.columns:
                country_to_continent_map = \
                df_ready[['Country', 'Continent']].drop_duplicates('Country').set_index('Country')[
                    'Continent'].to_dict()
            df_ready_2030_cagr = df_ready[df_ready['Year'] == 2030]
            if not df_ready_2030_cagr.empty and 'Country' in df_ready_2030_cagr.columns and 'CAGR_Forecast' in df_ready_2030_cagr.columns:
                country_to_cagr_map = \
                df_ready_2030_cagr[['Country', 'CAGR_Forecast']].drop_duplicates('Country').set_index('Country')[
                    'CAGR_Forecast'].to_dict()
            if 'Country' in df_ready.columns and 'ISO_Alpha3' in df_ready.columns:
                temp_iso_map_df = df_ready[['Country', 'ISO_Alpha3']].dropna(subset=['ISO_Alpha3']).drop_duplicates(
                    'Country')
                country_to_iso_map = temp_iso_map_df.set_index('Country')['ISO_Alpha3'].to_dict()
            else:
                country_to_iso_map = {}
        df_ready['Year'] = pd.to_numeric(df_ready['Year'], errors='coerce').astype('Int64')
        for col in ['GDP_per_capita', 'Type', 'Continent', 'ISO_Alpha3']:
            if col not in df_ready.columns: df_ready[col] = pd.NA if col != 'Type' else 'Dados Prontos'
        if 'Continent' not in df_ready.columns and 'Country' in df_ready.columns: df_ready['Continent'] = df_ready[
            'Country'].map(country_to_continent_map).fillna('Desconhecido')
        if 'ISO_Alpha3' not in df_ready.columns and 'Country' in df_ready.columns: df_ready['ISO_Alpha3'] = df_ready[
            'Country'].map(country_to_iso_map)

    df_h_path, df_h = dd / "gdp_per_capita.csv", pd.DataFrame()
    if df_h_path.exists():
        df_h_raw = pd.read_csv(df_h_path)
        df_h = df_h_raw.rename(columns={"Entity": "Country", "GDP per capita": "GDP_per_capita"})
        cols_h_needed = ['Country', 'Year', 'GDP_per_capita']
        missing_cols_h = [col for col in cols_h_needed if col not in df_h.columns]
        if missing_cols_h: st.error(f"Colunas {missing_cols_h} ausentes em {df_h_path}.")
        for col in missing_cols_h: df_h[col] = pd.NA
        df_h = df_h[cols_h_needed].copy()
        df_h.update(
            {"Type": "Historic", "Continent": df_h["Country"].map(country_to_continent_map).fillna("Desconhecido")})
        df_h["Year"] = pd.to_numeric(df_h["Year"], errors='coerce').astype('Int64')
        df_h["GDP_per_capita"] = pd.to_numeric(df_h["GDP_per_capita"], errors='coerce')
    else:
        st.error(f"Arquivo {df_h_path} não encontrado!");
        return pd.DataFrame(), pd.DataFrame(), df_ready

    df_f_path, df_f = dd / "gdp_forecast_to_2030.csv", pd.DataFrame()
    if df_f_path.exists():
        df_f_raw = pd.read_csv(df_f_path)
        df_f_renamed = df_f_raw.rename(columns={"Entity": "Country", "GDP per capita": "GDP_per_capita"})
        if 'Year' in df_f_renamed.columns:
            df_f_renamed['Year'] = pd.to_numeric(df_f_renamed['Year'], errors='coerce')
            df_f_filtered_year = df_f_renamed[df_f_renamed['Year'] == 2030].copy()
        else:
            st.error(f"Coluna 'Year' não encontrada em {df_f_path}."); df_f_filtered_year = df_f_renamed.copy()
        if 'Country' in df_f_filtered_year.columns and 'Year' in df_f_filtered_year.columns:
            df_f = df_f_filtered_year.drop_duplicates(subset=['Country', 'Year'], keep='last').copy()
        else:
            df_f = df_f_filtered_year.copy()
        if not df_f.empty:
            if "Type" in df_f.columns: df_f["Type_Original_CSV"] = df_f["Type"]
            df_f["Type"] = "Forecast"
            if 'Country' in df_f.columns:
                country_name_replacements = {"Eswatini": "Swaziland"}
                df_f['Country_for_ISO_map'] = df_f['Country'].replace(country_name_replacements)
                df_f["ISO_Alpha3"] = df_f["Country_for_ISO_map"].map(country_to_iso_map)
            else:
                df_f["ISO_Alpha3"] = pd.NA
            if 'Country' in df_f.columns:
                df_f["Continent"] = df_f["Country"].map(country_to_continent_map).fillna("Desconhecido")
                df_f["CAGR"] = df_f["Country"].map(country_to_cagr_map)
            else:
                df_f["Continent"], df_f["CAGR"] = "Desconhecido", pd.NA
            if "GDP_per_capita" in df_f.columns:
                df_f["GDP_per_capita"] = pd.to_numeric(df_f["GDP_per_capita"], errors='coerce')
            else:
                df_f["GDP_per_capita"] = pd.NA
            if 'CAGR' in df_f.columns and df_f["CAGR"].isnull().any() and isinstance(df_h,
                                                                                     pd.DataFrame) and not df_h.empty and all(
                    c in df_h.columns for c in ['Country', 'Year', 'GDP_per_capita']):
                df_h_for_cagr = df_h.dropna(subset=['Country', 'Year', 'GDP_per_capita'])
                if not df_h_for_cagr.empty:
                    latest_historical = df_h_for_cagr.loc[df_h_for_cagr.groupby('Country')['Year'].idxmax()][
                        ['Country', 'Year', 'GDP_per_capita']].rename(
                        columns={'Year': 'Last_Hist_Year', 'GDP_per_capita': 'Last_Hist_GDP'})
                    df_f_temp = pd.merge(df_f.copy(), latest_historical, on='Country', how='left')
                    mask_cagr_null = df_f_temp['CAGR'].isnull()
                    valid_calc_mask = (
                                df_f_temp['Last_Hist_GDP'].notna() & (df_f_temp['Last_Hist_GDP'] > 0) & df_f_temp[
                            'GDP_per_capita'].notna() & df_f_temp['Last_Hist_Year'].notna() & df_f_temp[
                                    'Year'].notna() & (
                                            (df_f_temp['Year'] - df_f_temp['Last_Hist_Year']) > 0) & mask_cagr_null)
                    df_f_temp['CAGR_calculated'] = pd.NA
                    df_f_temp.loc[valid_calc_mask, 'CAGR_calculated'] = ((df_f_temp.loc[
                                                                              valid_calc_mask, 'GDP_per_capita'] /
                                                                          df_f_temp.loc[
                                                                              valid_calc_mask, 'Last_Hist_GDP']) ** (
                                                                                     1 / (df_f_temp.loc[
                                                                                              valid_calc_mask, 'Year'] -
                                                                                          df_f_temp.loc[
                                                                                              valid_calc_mask, 'Last_Hist_Year']))) - 1
                    df_f['CAGR'] = df_f['CAGR'].fillna(df_f_temp['CAGR_calculated'])
            if 'CAGR' in df_f.columns:
                df_f['CAGR'] = pd.to_numeric(df_f['CAGR'], errors='coerce').fillna(0)
            else:
                df_f['CAGR'] = 0
    else:
        st.error(f"Arquivo {df_f_path} não encontrado!");
        return df_h, pd.DataFrame(), df_ready
    cols_to_keep_in_df_f = ['Country', 'Year', 'GDP_per_capita', 'Type', 'Continent', 'CAGR', 'ISO_Alpha3']
    if isinstance(df_f, pd.DataFrame) and not df_f.empty:
        if 'Country_for_ISO_map' in df_f.columns: df_f = df_f.drop(columns=['Country_for_ISO_map'])
        df_f = df_f[[col for col in cols_to_keep_in_df_f if col in df_f.columns]]
    else:
        df_f = pd.DataFrame(columns=cols_to_keep_in_df_f)
    cols_to_concat = ['Country', 'Year', 'GDP_per_capita', 'Continent', 'Type', 'ISO_Alpha3']
    dataframes_for_ts = []
    for df_orig, name in [(df_h, "df_h"), (df_f, "df_f"), (df_ready, "df_ready")]:
        if isinstance(df_orig, pd.DataFrame) and not df_orig.empty:
            temp_df = df_orig.copy()
            for col in cols_to_concat:
                if col not in temp_df.columns: temp_df[col] = pd.NA
            dataframes_for_ts.append(temp_df[cols_to_concat])
    if not dataframes_for_ts:
        df_ts = pd.DataFrame(columns=cols_to_concat)
    else:
        df_ts = pd.concat(dataframes_for_ts, ignore_index=True, sort=False)
        df_ts.dropna(subset=['Year', 'GDP_per_capita', 'Country'], inplace=True)
        df_ts["Year"] = pd.to_numeric(df_ts["Year"], errors='coerce').astype('Int64')
        df_ts["GDP_per_capita"] = pd.to_numeric(df_ts["GDP_per_capita"], errors='coerce')
    # st.sidebar.caption(f"load_data() concluído: {time.time() - load_start_time:.2f}s") # REMOVIDO
    return df_ts, df_f, df_ready


# --- Função para criar o mapa GLOBO PLOTLY ---
def create_plotly_globe_map(data_df):
    if not isinstance(data_df, pd.DataFrame) or data_df.empty:
        st.warning("Dados para o mapa Plotly Globo estão vazios ou inválidos.")
        return None
    required_cols = ['ISO_Alpha3', 'Country', 'GDP_per_capita', 'CAGR']  # CAGR adicionado para hover
    if not all(col in data_df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in data_df.columns]
        st.error(f"DataFrame para o mapa Plotly Globo não contém: {missing}")
        return None

    df_map_plot = data_df[data_df['Country'] != "Former Sudan"].copy()
    df_map_plot.dropna(subset=['ISO_Alpha3', 'GDP_per_capita'], inplace=True)
    if df_map_plot.empty:
        st.info("Não há dados válidos para exibir no mapa globo após filtros.")
        return None

    # Aplicar log ao PIB para melhor escala de cores
    df_map_plot['GDP_log'] = np.log(df_map_plot['GDP_per_capita'].apply(lambda x: x if x > 0 else 1))
    # Preparar CAGR para hover (formatado como string percentual)
    df_map_plot['CAGR_hover'] = df_map_plot['CAGR'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")

    fig = go.Figure(data=go.Choropleth(
        locations=df_map_plot['ISO_Alpha3'],
        z=df_map_plot['GDP_log'],
        customdata=df_map_plot[['Country', 'GDP_per_capita', 'CAGR_hover']],
        hovertemplate=(
                "<b>%{customdata[0]}</b><br><br>" +
                "PIB per Capita (2030): $%{customdata[1]:,.0f}<br>" +
                "CAGR (até 2030): %{customdata[2]}" +  # CAGR_hover já está formatado
                "<extra></extra>"
        ),
        colorscale='Reds',
        autocolorscale=False,
        reversescale=False,
        marker_line_color='#d1d1d1',
        marker_line_width=0.5,
        colorbar_title='PIB per Capita (log)',
        zmin=df_map_plot['GDP_log'].min() if not df_map_plot['GDP_log'].empty else None,
        zmax=df_map_plot['GDP_log'].max() if not df_map_plot['GDP_log'].empty else None
    ))

    fig.update_layout(
        title_text='',
        geo=dict(
            showframe=False, showcoastlines=False, projection_type='orthographic',
            showcountries=True, countrycolor='#d1d1d1',
            showocean=True, oceancolor='#c9d2e0',  # Cor clara para oceano, como no exemplo R
            showlakes=True, lakecolor='#99c0db',
            showrivers=True, rivercolor='#99c0db',
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=600,
        template="custom_dark_globe"  # Usa o template para fundo da página, mas geo define o globo
    )
    return fig


# Carregar dados
df_ts, df_fc, df_ready_data = load_data()


# ─── 5) FUNÇÃO PRINCIPAL ────────────────────────────────────────
def main():
    # Mensagens de debug da barra lateral principal foram comentadas/removidas
    if (df_fc.empty if isinstance(df_fc, pd.DataFrame) else True) and \
            (df_ts.empty if isinstance(df_ts, pd.DataFrame) else True):
        st.error("Dados essenciais não carregados.");
        st.stop()

    st.title("🌐 Dashboard de Previsão do PIB per Capita Global 2030")
    st.write("Análise histórica e projeções interativas do PIB per capita até 2030.")
    st.sidebar.header("Filtros Globais 🌍")

    unique_continents = []
    for df_check in [df_fc, df_ts]:
        if isinstance(df_check, pd.DataFrame) and not df_check.empty and 'Continent' in df_check.columns:
            unique_continents.extend(df_check["Continent"].dropna().unique())
    conts = ["Todos"] + sorted(list(set(unique_continents))) if unique_continents else ["Todos"]
    sel_cont = st.sidebar.selectbox("Selecione o Continente:", conts, index=0, key="sb_continent")

    df_sel = pd.DataFrame()
    if isinstance(df_fc, pd.DataFrame) and not df_fc.empty:
        if sel_cont == "Todos":
            df_sel = df_fc.copy()
        else:
            if 'Continent' in df_fc.columns: df_sel = df_fc[df_fc["Continent"] == sel_cont].copy()

    st.sidebar.selectbox("Ano p/ Visão Global:", [2030], index=0, disabled=True, key="sb_year_global")
    st.sidebar.markdown("---");
    st.sidebar.write("Desenvolvido por Douglas Souza")
    st.sidebar.markdown("[Repositório GitHub](#) • [Perfil LinkedIn](#)")

    m2030, pm, mean2030, cgr_ct, cgr_val = 0, "N/A", 0, "N/A", 0.0
    if isinstance(df_sel, pd.DataFrame) and not df_sel.empty:
        if 'GDP_per_capita' in df_sel.columns and df_sel['GDP_per_capita'].notna().any():
            m2030 = df_sel["GDP_per_capita"].max()
            try:
                idx_max_gdp = df_sel["GDP_per_capita"].dropna().idxmax()
            except ValueError:
                idx_max_gdp = None
            if idx_max_gdp is not None: pm_row = df_sel.loc[idx_max_gdp]; pm = pm_row["Country"] if pd.notna(
                pm_row["Country"]) else "N/A"
            mean2030 = df_sel["GDP_per_capita"].mean()
        if "CAGR" in df_sel.columns and df_sel["CAGR"].notna().any():
            try:
                idx_max_cagr = df_sel["CAGR"].dropna().idxmax()
                if idx_max_cagr is not None: cgr_max_row = df_sel.loc[idx_max_cagr]; cgr_ct = cgr_max_row[
                    "Country"] if pd.notna(cgr_max_row["Country"]) else "N/A"; cgr_val = cgr_max_row[
                    "CAGR"] if pd.notna(cgr_max_row["CAGR"]) else 0.0
            except ValueError:
                cgr_ct, cgr_val = "N/A", 0.0
        else:
            cgr_ct, cgr_val = "N/A", 0.0
    c1, c2, c3, c4 = st.columns(4, gap="large")
    c1.metric("Maior PIB/Cap (2030)", f"${m2030:,.0f}" if pd.notna(m2030) and m2030 != 0 else "N/A")
    c2.metric("País Top PIB", pm);
    c3.metric("Média PIB/Cap (Sel.)", f"${mean2030:,.0f}" if pd.notna(mean2030) and mean2030 != 0 else "N/A")
    c4.metric("Maior CAGR", f"{cgr_ct} ({cgr_val:.2%})" if pd.notna(cgr_val) and cgr_ct != "N/A" else "N/A")
    st.markdown("---")

    tabs = st.tabs(["Série Temporal", "Ranking & CAGR", "Visão Global (Mapa)", "Sobre o Modelo"])

    with tabs[0]:
        st.subheader("Série Temporal: Histórico vs. Previsão")
        df_ts_current = df_ts.copy() if isinstance(df_ts, pd.DataFrame) else pd.DataFrame()
        if not df_ts_current.empty and sel_cont != "Todos" and 'Continent' in df_ts_current.columns:
            df_ts_current = df_ts_current[df_ts_current["Continent"] == sel_cont]
        if not df_ts_current.empty and 'Country' in df_ts_current.columns:
            countries_available = sorted(df_ts_current["Country"].dropna().unique())
            default_countries = countries_available[:min(5, len(countries_available))]
            sel_ct = st.multiselect("Selecione até 5 países:", countries_available, default=default_countries,
                                    max_selections=5, key="countries_timeseries")
            if sel_ct:
                df_plot = df_ts_current[df_ts_current["Country"].isin(sel_ct)].sort_values(
                    by=['Country', 'Type', 'Year'])
                if not df_plot.empty and 'Year' in df_plot.columns and 'GDP_per_capita' in df_plot.columns:
                    fig_ts_plotly = px.line(df_plot, x="Year", y="GDP_per_capita", color="Country", line_dash="Type",
                                            markers=True,
                                            labels={"GDP_per_capita": "PIB per Capita (USD)", "Year": "Ano"})
                    fig_ts_plotly.update_layout(yaxis_tickformat="$,.0f")
                    st.plotly_chart(fig_ts_plotly, use_container_width=True)
                else:
                    st.info("Nenhum dado para plotar.")
            elif countries_available:
                st.info("Selecione país(es) para visualizar.")
            else:
                st.info(f"Sem dados de séries temporais para '{sel_cont}'.")
        else:
            st.info("Sem dados de séries temporais.")

    with tabs[1]:
        st.subheader("Top/Bottom CAGR Previsto")
        df_sel_current = df_sel.copy() if isinstance(df_sel, pd.DataFrame) else pd.DataFrame()
        if not df_sel_current.empty and "CAGR" in df_sel_current.columns and df_sel_current["CAGR"].notna().any():
            df_sel_cagr = df_sel_current.dropna(subset=['CAGR'])
            if not df_sel_cagr.empty:
                n_countries_available = df_sel_cagr['Country'].nunique()
                n = 0;
                show_slider = False
                if n_countries_available == 0:
                    st.info("Não há países com dados de CAGR válidos para exibir um ranking.")
                elif n_countries_available == 1:
                    n = 1
                else:
                    show_slider = True;
                    slider_min_val = 1;
                    slider_max_val = min(20, n_countries_available)
                    slider_default_val = min(10, slider_max_val);
                    slider_default_val = max(slider_min_val, slider_default_val)
                    n = st.slider("Número de países para ranking:", min_value=slider_min_val, max_value=slider_max_val,
                                  value=slider_default_val, key="ranking_slider")
                if n > 0:
                    top = df_sel_cagr.nlargest(n, "CAGR");
                    bot = df_sel_cagr.nsmallest(n, "CAGR")
                    col_top, col_bot = st.columns(2)
                    if not top.empty:
                        fig_top_cagr = px.bar(top.sort_values("CAGR", ascending=True), x="CAGR", y="Country",
                                              orientation="h", title="Top CAGR", color="CAGR",
                                              color_continuous_scale=px.colors.sequential.Viridis,
                                              labels={"CAGR": "CAGR (%)", "Country": "País"})
                        fig_top_cagr.update_layout(xaxis_tickformat=".2%");
                        col_top.plotly_chart(fig_top_cagr, use_container_width=True)
                    else:
                        col_top.info("Sem dados para Top CAGR.")
                    if not bot.empty:
                        fig_bot_cagr = px.bar(bot.sort_values("CAGR", ascending=False), x="CAGR", y="Country",
                                              orientation="h", title="Bottom CAGR", color="CAGR",
                                              color_continuous_scale=px.colors.sequential.Rainbow_r,
                                              labels={"CAGR": "CAGR (%)", "Country": "País"})
                        fig_bot_cagr.update_layout(xaxis_tickformat=".2%");
                        col_bot.plotly_chart(fig_bot_cagr, use_container_width=True)
                    else:
                        col_bot.info("Sem dados para Bottom CAGR.")
            else:
                st.info("Não há dados de CAGR válidos após a remoção de NaNs para exibir os rankings.")
        else:
            st.info("Dados de CAGR insuficientes ou ausentes nos filtros selecionados para exibir os rankings.")

    with tabs[2]:
        st.subheader("Visão Global do PIB per Capita (2030) - Globo Interativo")
        df_map_input = df_fc.copy() if isinstance(df_fc, pd.DataFrame) else pd.DataFrame()
        if not df_map_input.empty and 'ISO_Alpha3' in df_map_input.columns:
            df_map_input_2030 = df_map_input[df_map_input['Year'] == 2030].copy()
            if not df_map_input_2030.empty and df_map_input_2030['ISO_Alpha3'].notna().any():
                plotly_globe_fig = create_plotly_globe_map(df_map_input_2030)
                if plotly_globe_fig:
                    st.plotly_chart(plotly_globe_fig, use_container_width=True)
                else:
                    st.error("Não foi possível gerar o mapa globo Plotly.")
            elif df_map_input_2030.empty:
                st.info("Sem dados para 2030 para o mapa globo.")
            else:
                st.warning("Dados 'ISO_Alpha3' ausentes/inválidos em 'df_fc' para mapa.")
                st.info("Verifique se 'gdp_dashboard_ready_data.csv' fornece 'Swaziland' com ISO 'SWZ'.")
        else:
            st.warning("Dados de 'df_fc' ou coluna 'ISO_Alpha3' ausentes para o mapa.")

    with tabs[3]:
        st.subheader("Sobre o Modelo e Confiabilidade")
        mae_teste, r2_teste, mse_teste = 178.14, 0.9885, 937337
        st.markdown(
            f"""- **Modelo:** LSTM (Keras), otimizado com Optuna.\n- **Métricas (Teste):** MAE: ${mae_teste:,.2f}, R²: {r2_teste:.4f}, MSE: {mse_teste:,.2f}\n> **Nota:** Projeções de longo prazo são inerentemente incertas.""")

    st.markdown("---")
    st.subheader("Dados Detalhados (Previsão 2030)")
    df_sel_current_aggrid = df_sel.copy() if isinstance(df_sel, pd.DataFrame) else pd.DataFrame()
    if not df_sel_current_aggrid.empty:
        try:
            csv_export = df_sel_current_aggrid.to_csv(index=False).encode("utf-8")
            st.download_button(label="📥 Exportar Seleção para CSV", data=csv_export,
                               file_name=f"forecast_2030_{sel_cont.lower().replace(' ', '_')}.csv", mime="text/csv")
        except Exception as e:
            st.warning(f"Erro ao gerar CSV: {e}")
        gb = GridOptionsBuilder.from_dataframe(df_sel_current_aggrid)
        gb.configure_default_column(filter=True, sortable=True, resizable=True, groupable=True)
        if 'GDP_per_capita' in df_sel_current_aggrid.columns: gb.configure_column("GDP_per_capita",
                                                                                  type=["numericColumn"],
                                                                                  valueFormatter="'$' + value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})")
        if 'CAGR' in df_sel_current_aggrid.columns: gb.configure_column("CAGR", type=["numericColumn"],
                                                                        valueFormatter="value == null ? '' : (typeof value === 'number' ? (value * 100).toFixed(2) + '%' : '')")
        gridOptions = gb.build()
        AgGrid(df_sel_current_aggrid, gridOptions=gridOptions, theme="streamlit-dark", fit_columns_on_grid_load=True,
               allow_unsafe_jscode=True, enable_enterprise_modules=False)
    else:
        st.info("Sem dados detalhados.")

    st.markdown("---")
    try:
        hoje = pd.Timestamp.now(tz="America/Bahia").strftime("%Y-%m-%d %H:%M:%S %Z")
        data_atualizacao = pd.Timestamp.today().strftime('%Y-%m-%d')
    except Exception:
        hoje = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        data_atualizacao = pd.Timestamp.today().strftime('%Y-%m-%d')
    st.write(f"Dados (base) atualizados em {data_atualizacao}. Acessado em: {hoje}.")


if __name__ == "__main__":
    main()