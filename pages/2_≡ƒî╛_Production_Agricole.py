"""
Dashboard exploratoire — FactCropProduction (OCP DataFlow)
=============================================================

Objectif : valider que le modèle dimensionnel (DimDate, DimCountry,
DimCrop, DimElement, FactCropProduction) répond à la question métier :
« Comment évolue la production agricole mondiale (blé, maïs, riz, soja...),
en tant qu'indicateur indirect de la demande en intrants agricoles, et
quels pays en sont les principaux moteurs ? »

Fait partie de l'app multi-pages (voir Home.py à la racine).

Configuration : variables d'environnement (ou fichier .env à la racine)
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

st.set_page_config(page_title="OCP DataFlow — Production agricole", page_icon="🌾", layout="wide")

# ---------------------------------------------------------------------------
# Connexion à la base
# ---------------------------------------------------------------------------

@st.cache_resource
def get_engine():
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "ocp_dataflow")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


@st.cache_data(ttl=600)
def load_countries() -> pd.DataFrame:
    return pd.read_sql(
        'SELECT country_code, country_name FROM ocp_dataflow."DimCountry" ORDER BY country_name;',
        get_engine(),
    )


@st.cache_data(ttl=600)
def load_crops() -> pd.DataFrame:
    return pd.read_sql(
        'SELECT crop_code, crop_name FROM ocp_dataflow."DimCrop" ORDER BY crop_name;',
        get_engine(),
    )


@st.cache_data(ttl=600)
def load_elements() -> pd.DataFrame:
    return pd.read_sql(
        'SELECT element_code, element_name, unit FROM ocp_dataflow."DimElement" ORDER BY element_name;',
        get_engine(),
    )


@st.cache_data(ttl=600)
def load_crop_production(
    country_codes: list[int], crop_codes: list[int], element_codes: list[int],
    year_start: int, year_end: int,
) -> pd.DataFrame:
    if not (country_codes and crop_codes and element_codes):
        return pd.DataFrame()
    query = """
        SELECT
            d.year,
            co.country_code, co.country_name,
            cr.crop_code, cr.crop_name,
            el.element_name, el.unit,
            f.value
        FROM ocp_dataflow."FactCropProduction" f
        JOIN ocp_dataflow."DimDate" d ON d.full_date = f.full_date
        JOIN ocp_dataflow."DimCountry" co ON co.country_code = f.country_code
        JOIN ocp_dataflow."DimCrop" cr ON cr.crop_code = f.crop_code
        JOIN ocp_dataflow."DimElement" el ON el.element_code = f.element_code
        WHERE f.country_code = ANY(%(country_codes)s)
          AND f.crop_code = ANY(%(crop_codes)s)
          AND f.element_code = ANY(%(element_codes)s)
          AND d.year BETWEEN %(year_start)s AND %(year_end)s
        ORDER BY d.year;
    """
    return pd.read_sql(
        query, get_engine(),
        params={
            "country_codes": country_codes, "crop_codes": crop_codes,
            "element_codes": element_codes, "year_start": year_start, "year_end": year_end,
        },
    )


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("🌾 Production agricole mondiale")
st.caption("Domaine : Agriculture — Table de faits : FactCropProduction — Grain : Pays + Culture + Année + Élément")

try:
    countries_df = load_countries()
    crops_df = load_crops()
    elements_df = load_elements()
except Exception as e:
    st.error(
        "Impossible de se connecter à la base PostgreSQL. "
        "Vérifie les variables POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD."
    )
    st.exception(e)
    st.stop()

if countries_df.empty or crops_df.empty or elements_df.empty:
    st.warning("Dimensions vides (DimCountry / DimCrop / DimElement). As-tu déjà lancé le pipeline ETL FAOSTAT ?")
    st.stop()

# --- Filtres (sidebar) ---
st.sidebar.header("Filtres")

default_crops = crops_df["crop_name"].tolist()[:5] if len(crops_df) > 5 else crops_df["crop_name"].tolist()
selected_crops = st.sidebar.multiselect("Cultures", options=crops_df["crop_name"].tolist(), default=default_crops)

default_countries = countries_df["country_name"].tolist()[:10]
selected_countries = st.sidebar.multiselect(
    "Pays", options=countries_df["country_name"].tolist(), default=default_countries,
)

selected_elements = st.sidebar.multiselect(
    "Indicateur (élément)", options=elements_df["element_name"].tolist(), default=elements_df["element_name"].tolist(),
)

year_start, year_end = st.sidebar.slider("Années", 2020, 2024, (2020, 2024))

if not (selected_crops and selected_countries and selected_elements):
    st.info("Sélectionne au moins une culture, un pays et un indicateur dans le panneau de gauche.")
    st.stop()

crop_codes = crops_df.loc[crops_df["crop_name"].isin(selected_crops), "crop_code"].tolist()
country_codes = countries_df.loc[countries_df["country_name"].isin(selected_countries), "country_code"].tolist()
element_codes = elements_df.loc[elements_df["element_name"].isin(selected_elements), "element_code"].tolist()

df = load_crop_production(country_codes, crop_codes, element_codes, year_start, year_end)

if df.empty:
    st.warning("Aucune donnée pour cette combinaison de filtres.")
    st.stop()

# --- KPIs ---
st.subheader("Aperçu")
latest_year = int(df["year"].max())
latest = df[df["year"] == latest_year]
top_producer = latest.groupby("country_name")["value"].sum().sort_values(ascending=False)

kpi_cols = st.columns(3)
kpi_cols[0].metric("Année la plus récente", latest_year)
kpi_cols[1].metric("Production totale (année, filtres actifs)", f"{latest['value'].sum():,.0f}")
kpi_cols[2].metric("Premier producteur", top_producer.index[0] if not top_producer.empty else "—")

# --- Évolution par culture ---
st.subheader("Évolution de la production par culture")
trend_df = df.groupby(["year", "crop_name"], as_index=False)["value"].sum()
fig_trend = px.line(
    trend_df, x="year", y="value", color="crop_name", markers=True,
    labels={"year": "Année", "value": "Production", "crop_name": "Culture"},
)
st.plotly_chart(fig_trend, use_container_width=True)

# --- Top pays producteurs ---
st.subheader(f"Top pays producteurs — {latest_year}")
top_n = st.slider("Nombre de pays affichés", 5, 20, 10)
top_df = (
    latest.groupby("country_name", as_index=False)["value"].sum()
    .sort_values("value", ascending=False).head(top_n)
)
fig_top = px.bar(
    top_df, x="value", y="country_name", orientation="h",
    labels={"value": "Production", "country_name": "Pays"},
)
fig_top.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig_top, use_container_width=True)

# --- Table brute ---
with st.expander("Voir les données brutes"):
    st.dataframe(df.sort_values(["year", "value"], ascending=[False, False]), use_container_width=True)
    st.download_button(
        "Télécharger en CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="fact_crop_production_export.csv",
        mime="text/csv",
    )
