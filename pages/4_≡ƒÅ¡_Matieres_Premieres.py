"""
Dashboard exploratoire — FactCommodityPrices (OCP DataFlow)
===============================================================

Objectif : valider que le modèle dimensionnel (DimDate, DimCommodity,
FactCommodityPrices) répond à la question métier :
« Comment évoluent les prix mondiaux des phosphates et des engrais ? »

Fait partie de l'app multi-pages (voir Home.py à la racine).

Configuration : variables d'environnement (ou fichier .env à la racine)
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

st.set_page_config(page_title="OCP DataFlow — Matières premières", page_icon="🏭", layout="wide")

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
def load_commodities() -> pd.DataFrame:
    return pd.read_sql(
        'SELECT commodity_name, commodity_code, unit FROM ocp_dataflow."DimCommodity" ORDER BY commodity_name;',
        get_engine(),
    )


@st.cache_data(ttl=600)
def load_commodity_prices(commodity_names: list[str], start: date, end: date) -> pd.DataFrame:
    if not commodity_names:
        return pd.DataFrame()
    query = """
        SELECT f.full_date, c.commodity_code, c.commodity_name, c.unit, f.price
        FROM ocp_dataflow."FactCommodityPrices" f
        JOIN ocp_dataflow."DimCommodity" c ON c.commodity_name = f.commodity_name
        WHERE f.commodity_name = ANY(%(commodity_names)s)
          AND f.full_date BETWEEN %(start)s AND %(end)s
        ORDER BY f.full_date;
    """
    return pd.read_sql(
        query, get_engine(),
        params={"commodity_names": commodity_names, "start": start, "end": end},
    )


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("🏭 Prix mondiaux des matières premières")
st.caption("Domaine : Matières premières — Table de faits : FactCommodityPrices — Grain : Matière première + Mois")

try:
    commodities_df = load_commodities()
except Exception as e:
    st.error(
        "Impossible de se connecter à la base PostgreSQL. "
        "Vérifie les variables POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD."
    )
    st.exception(e)
    st.stop()

if commodities_df.empty:
    st.warning("Aucune matière première trouvée dans DimCommodity. As-tu déjà lancé le pipeline ETL World Bank ?")
    st.stop()

# --- Filtres (sidebar) ---
st.sidebar.header("Filtres")

default_commodities = [
    c for c in commodities_df["commodity_name"].tolist()
    if any(k in c.lower() for k in ["phosphate", "dap", "tsp", "urea"])
] or commodities_df["commodity_name"].tolist()[:5]

selected_names = st.sidebar.multiselect(
    "Matières premières", options=commodities_df["commodity_name"].tolist(), default=default_commodities,
)

today = date.today()
start_date, end_date = st.sidebar.date_input("Période", value=(today - timedelta(days=365 * 3), today))

if not selected_names:
    st.info("Sélectionne au moins une matière première dans le panneau de gauche.")
    st.stop()

df = load_commodity_prices(selected_names, start_date, end_date)

if df.empty:
    st.warning("Aucune donnée sur cette période pour les matières sélectionnées.")
    st.stop()

# --- KPIs ---
st.subheader("Aperçu")
latest = df.sort_values("full_date").groupby("commodity_name").tail(1)
first = df.sort_values("full_date").groupby("commodity_name").head(1)[["commodity_name", "price"]].rename(
    columns={"price": "price_first"}
)
kpi_df = latest.merge(first, on="commodity_name")
kpi_df["variation_pct"] = (kpi_df["price"] - kpi_df["price_first"]) / kpi_df["price_first"] * 100

kpi_cols = st.columns(len(kpi_df))
for col, (_, row) in zip(kpi_cols, kpi_df.iterrows()):
    col.metric(
        label=f"{row['commodity_name']} ({row['unit']})",
        value=f"{row['price']:.1f}",
        delta=f"{row['variation_pct']:.1f} % sur la période",
    )

# --- Graphique ---
st.subheader("Évolution des prix")
fig = px.line(
    df, x="full_date", y="price", color="commodity_name",
    labels={"full_date": "Date", "price": "Prix", "commodity_name": "Matière première"},
    hover_data=["unit"],
)
fig.update_layout(hovermode="x unified", legend_title_text="")
st.plotly_chart(fig, use_container_width=True)

# --- Table brute ---
with st.expander("Voir les données brutes"):
    st.dataframe(df.sort_values(["commodity_name", "full_date"], ascending=[True, False]), use_container_width=True)
    st.download_button(
        "Télécharger en CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="fact_commodity_prices_export.csv",
        mime="text/csv",
    )
