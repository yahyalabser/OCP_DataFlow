"""
Dashboard exploratoire — FactFoodPriceIndex (OCP DataFlow)
==============================================================

Objectif : valider que le modèle dimensionnel (DimDate, FactFoodPriceIndex)
répond à la question métier :
« Quel est l'impact du contexte agricole mondial (Food Price Index,
production agricole, etc.) sur le marché des engrais ? »

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

st.set_page_config(page_title="OCP DataFlow — Indice des prix alimentaires", page_icon="🍞", layout="wide")

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
def load_food_price_index(start: date, end: date) -> pd.DataFrame:
    query = """
        SELECT full_date, food_index, meat_price, dairy_price,
               cereals_price, oils_price, sugar_price
        FROM ocp_dataflow."FactFoodPriceIndex"
        WHERE full_date BETWEEN %(start)s AND %(end)s
        ORDER BY full_date;
    """
    return pd.read_sql(query, get_engine(), params={"start": start, "end": end})


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("🍞 Indice mondial des prix alimentaires (FFPI)")
st.caption("Domaine : Food Price Index — Table de faits : FactFoodPriceIndex — Grain : Mois")

st.sidebar.header("Filtres")
today = date.today()
start_date, end_date = st.sidebar.date_input("Période", value=(today - timedelta(days=365 * 3), today))

series_options = {
    "food_index": "Indice global (FFPI)",
    "meat_price": "Viande",
    "dairy_price": "Produits laitiers",
    "cereals_price": "Céréales",
    "oils_price": "Huiles",
    "sugar_price": "Sucre",
}
selected_series = st.sidebar.multiselect(
    "Sous-indices à afficher",
    options=list(series_options.keys()),
    default=list(series_options.keys()),
    format_func=lambda k: series_options[k],
)

try:
    df = load_food_price_index(start_date, end_date)
except Exception as e:
    st.error(
        "Impossible de se connecter à la base PostgreSQL. "
        "Vérifie les variables POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD."
    )
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("Aucune donnée sur cette période. As-tu déjà lancé le pipeline ETL FFPI ?")
    st.stop()

if not selected_series:
    st.info("Sélectionne au moins un sous-indice dans le panneau de gauche.")
    st.stop()

# --- KPIs ---
st.subheader("Aperçu")
df_sorted = df.sort_values("full_date")
latest = df_sorted.iloc[-1]
previous = df_sorted.iloc[-2] if len(df_sorted) > 1 else latest

kpi_cols = st.columns(len(selected_series))
for col, s in zip(kpi_cols, selected_series):
    delta = latest[s] - previous[s]
    col.metric(label=series_options[s], value=f"{latest[s]:.1f}", delta=f"{delta:+.1f} vs mois précédent")

# --- Graphique ---
st.subheader("Évolution des indices")
melted = df.melt(id_vars="full_date", value_vars=selected_series, var_name="serie", value_name="valeur")
melted["serie"] = melted["serie"].map(series_options)
fig = px.line(
    melted, x="full_date", y="valeur", color="serie",
    labels={"full_date": "Date", "valeur": "Indice (base 100 = 2014-2016)", "serie": ""},
)
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# --- Table brute ---
with st.expander("Voir les données brutes"):
    st.dataframe(df.sort_values("full_date", ascending=False), use_container_width=True)
    st.download_button(
        "Télécharger en CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="fact_food_price_index_export.csv",
        mime="text/csv",
    )
