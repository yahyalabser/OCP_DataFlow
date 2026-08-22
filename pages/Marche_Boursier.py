"""
Dashboard exploratoire — FactStockPrices (OCP DataFlow)
=========================================================

Objectif : valider que le modèle dimensionnel (DimDate, DimCompany,
FactStockPrices) répond bien à la question métier :
« Comment évoluent les performances boursières des principaux
concurrents d'OCP ? »

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
def load_companies() -> pd.DataFrame:
    query = """
        SELECT company_key, symbol, company_name, sector
        FROM ocp_dataflow."DimCompany"
        ORDER BY symbol;
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_stock_prices(symbols: list[str], start: date, end: date) -> pd.DataFrame:
    if not symbols:
        return pd.DataFrame()
    query = """
        SELECT
            f.full_date,
            c.symbol,
            c.company_name,
            c.sector,
            f.open, f.high, f.low, f.close, f.volume
        FROM ocp_dataflow."FactStockPrices" f
        JOIN ocp_dataflow."DimCompany" c ON c.symbol = f.symbol
        WHERE f.symbol = ANY(%(symbols)s)
          AND f.full_date BETWEEN %(start)s AND %(end)s
        ORDER BY f.full_date;
    """
    return pd.read_sql(
        query, get_engine(),
        params={"symbols": symbols, "start": start, "end": end},
    )


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.set_page_config(page_title="OCP DataFlow — Marché boursier", page_icon="📈", layout="wide")
st.title("📈 Performances boursières des concurrents")
st.caption("Domaine : Marché boursier — Table de faits : FactStockPrices — Grain : Entreprise + Jour")

try:
    companies_df = load_companies()
except Exception as e:
    st.error(
        "Impossible de se connecter à la base PostgreSQL. "
        "Vérifie les variables POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD."
    )
    st.exception(e)
    st.stop()

if companies_df.empty:
    st.warning("Aucune entreprise trouvée dans DimCompany. As-tu déjà lancé le pipeline ETL ?")
    st.stop()

# --- Filtres (sidebar) ---
st.sidebar.header("Filtres")

default_symbols = companies_df["symbol"].tolist()
selected_symbols = st.sidebar.multiselect(
    "Entreprises",
    options=companies_df["symbol"].tolist(),
    default=default_symbols,
    format_func=lambda s: f"{s} — {companies_df.loc[companies_df.symbol == s, 'company_name'].values[0]}",
)

today = date.today()
start_date, end_date = st.sidebar.date_input(
    "Période",
    value=(today - timedelta(days=180), today),
)

if not selected_symbols:
    st.info("Sélectionne au moins une entreprise dans le panneau de gauche.")
    st.stop()

df = load_stock_prices(selected_symbols, start_date, end_date)

if df.empty:
    st.warning("Aucune donnée sur cette période pour les entreprises sélectionnées.")
    st.stop()

# --- KPIs ---
st.subheader("Aperçu")
latest = df.sort_values("full_date").groupby("symbol").tail(1)
first = df.sort_values("full_date").groupby("symbol").head(1)[["symbol", "close"]].rename(columns={"close": "close_first"})
kpi_df = latest.merge(first, on="symbol")
kpi_df["variation_pct"] = (kpi_df["close"] - kpi_df["close_first"]) / kpi_df["close_first"] * 100

cols = st.columns(len(kpi_df))
for col, (_, row) in zip(cols, kpi_df.iterrows()):
    col.metric(
        label=row["symbol"],
        value=f"{row['close']:.2f}",
        delta=f"{row['variation_pct']:.1f} % sur la période",
    )

# --- Graphique : cours de clôture ---
st.subheader("Cours de clôture")
fig_close = px.line(
    df, x="full_date", y="close", color="symbol",
    labels={"full_date": "Date", "close": "Clôture", "symbol": "Entreprise"},
    hover_data=["company_name", "sector"],
)
fig_close.update_layout(hovermode="x unified", legend_title_text="")
st.plotly_chart(fig_close, use_container_width=True)

# --- Graphique : volume ---
st.subheader("Volume échangé")
fig_vol = px.bar(
    df, x="full_date", y="volume", color="symbol",
    labels={"full_date": "Date", "volume": "Volume", "symbol": "Entreprise"},
)
st.plotly_chart(fig_vol, use_container_width=True)

# --- Table brute ---
with st.expander("Voir les données brutes"):
    st.dataframe(
        df.sort_values(["symbol", "full_date"], ascending=[True, False]),
        use_container_width=True,
    )
    st.download_button(
        "Télécharger en CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="fact_stock_prices_export.csv",
        mime="text/csv",
    )
