"""
Dashboard exploratoire — FactOCPFinancials (OCP DataFlow)
=============================================================

Objectif : valider que le modèle dimensionnel (DimDate, FactOCPFinancials)
répond à la question métier :
« Comment les performances financières d'OCP (chiffre d'affaires, EBITDA,
marge, résultat net) se comparent-elles, en évolution relative, à celles
de ses concurrents cotés en bourse ? »

Note : les montants sont en MAD et ne sont pas directement comparables aux
concurrents cotés en USD (FactStockPrices) sans conversion de devise.
Utilise quarter_label comme clé de comparaison analytique entre domaines
plutôt qu'une comparaison directe des dates : full_date correspond ici à
la date de publication du communiqué (published_at côté source), pas à
la date de fin du trimestre concerné.

Fait partie de l'app multi-pages (voir Home.py à la racine).

Configuration : variables d'environnement (ou fichier .env à la racine)
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

st.set_page_config(page_title="OCP DataFlow — Finances OCP", page_icon="🏦", layout="wide")

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
def load_ocp_financials() -> pd.DataFrame:
    query = """
        SELECT full_date, quarter_label, revenue, ebitda, ebitda_margin, net_income
        FROM ocp_dataflow."FactOCPFinancials"
        ORDER BY full_date;
    """
    return pd.read_sql(query, get_engine())


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("🏦 Performance financière d'OCP")
st.caption("Domaine : Finances OCP — Table de faits : FactOCPFinancials — Grain : Trimestre")

try:
    df = load_ocp_financials()
except Exception as e:
    st.error(
        "Impossible de se connecter à la base PostgreSQL. "
        "Vérifie les variables POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD."
    )
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("Aucune donnée dans FactOCPFinancials. As-tu déjà saisi les communiqués trimestriels ?")
    st.stop()

# --- Filtres (sidebar) ---
st.sidebar.header("Filtres")
selected_quarters = st.sidebar.multiselect(
    "Trimestres", options=df["quarter_label"].tolist(), default=df["quarter_label"].tolist(),
)

if not selected_quarters:
    st.info("Sélectionne au moins un trimestre dans le panneau de gauche.")
    st.stop()

df = df[df["quarter_label"].isin(selected_quarters)].sort_values("full_date")

st.caption("⚠️ Montants en MAD — non directement comparables aux concurrents cotés (USD) sans conversion de devise.")

# --- KPIs ---
st.subheader("Aperçu")
latest = df.iloc[-1]
previous = df.iloc[-2] if len(df) > 1 else latest

kpi_cols = st.columns(4)
kpi_cols[0].metric("Trimestre le plus récent", latest["quarter_label"])
kpi_cols[1].metric(
    "Chiffre d'affaires (MAD)",
    f"{latest['revenue']:,.0f}",
    delta=f"{(latest['revenue'] - previous['revenue']) / previous['revenue'] * 100:+.1f} %" if previous["revenue"] else None,
)
kpi_cols[2].metric(
    "EBITDA (MAD)",
    f"{latest['ebitda']:,.0f}",
    delta=f"{(latest['ebitda'] - previous['ebitda']) / previous['ebitda'] * 100:+.1f} %" if previous["ebitda"] else None,
)
kpi_cols[3].metric(
    "Marge EBITDA",
    f"{latest['ebitda_margin'] * 100:.1f} %",
    delta=f"{(latest['ebitda_margin'] - previous['ebitda_margin']) * 100:+.1f} pts",
)

# --- Graphique : revenue / ebitda / net income ---
st.subheader("Chiffre d'affaires, EBITDA et résultat net par trimestre")
fig_bars = go.Figure()
fig_bars.add_bar(x=df["quarter_label"], y=df["revenue"], name="Chiffre d'affaires")
fig_bars.add_bar(x=df["quarter_label"], y=df["ebitda"], name="EBITDA")
fig_bars.add_bar(x=df["quarter_label"], y=df["net_income"], name="Résultat net")
fig_bars.update_layout(barmode="group", xaxis_title="Trimestre", yaxis_title="MAD", legend_title_text="")
st.plotly_chart(fig_bars, use_container_width=True)

# --- Marge EBITDA ---
st.subheader("Évolution de la marge EBITDA")
fig_margin = px.line(
    df, x="quarter_label", y="ebitda_margin", markers=True,
    labels={"quarter_label": "Trimestre", "ebitda_margin": "Marge EBITDA"},
)
fig_margin.update_yaxes(tickformat=".0%")
st.plotly_chart(fig_margin, use_container_width=True)

# --- Table brute ---
with st.expander("Voir les données brutes"):
    display_df = df.copy()
    display_df["ebitda_margin"] = (display_df["ebitda_margin"] * 100).round(2)
    st.dataframe(display_df.sort_values("full_date", ascending=False), use_container_width=True)
    st.download_button(
        "Télécharger en CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="fact_ocp_financials_export.csv",
        mime="text/csv",
    )
