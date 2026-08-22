"""
OCP DataFlow — Fenêtre principale (Home)
==========================================

Point d'entrée de l'application Streamlit multi-pages.
Donne une vue d'ensemble du Data Warehouse et des liens vers
les 6 dashboards (un par Star Schema / Data Mart).

Lancement (depuis la racine du projet, à côté du dossier pages/) :
    pip install -r requirements.txt
    streamlit run Home.py

Configuration : variables d'environnement (ou fichier .env à la racine)
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

from datetime import datetime
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

st.set_page_config(
    page_title="OCP DataFlow — Accueil",
    page_icon="🛰️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Connexion à la base (même convention que les autres pages)
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


@st.cache_data(ttl=300)
def load_row_counts() -> pd.DataFrame:
    tables = [
        "FactStockPrices",
        "FactCropProduction",
        "FactFoodPriceIndex",
        "FactCommodityPrices",
        "FactNews",
        "FactOCPFinancials",
    ]
    rows = []
    engine = get_engine()
    with engine.connect() as conn:
        for t in tables:
            try:
                n = conn.exec_driver_sql(f'SELECT COUNT(*) FROM ocp_dataflow."{t}";').scalar()
            except Exception:
                n = None
            rows.append({"table": t, "rows": n})
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_last_etl_runs() -> pd.DataFrame:
    query = """
        SELECT source, run_datetime, status, rows_extracted, rows_loaded, duration_seconds
        FROM ocp_dataflow."EtlRunLog"
        ORDER BY source, run_datetime DESC;
    """
    return pd.read_sql(query, get_engine())


# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------

col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.title("OCP DataFlow — Data Warehouse Marché des Phosphates & Engrais")
with col_refresh:
    st.write("")
    if st.button("Rafraîchir", help="Vide le cache et recharge les données depuis la base"):
        st.cache_data.clear()
        st.rerun()
st.caption(
    "Vision unifiée du marché mondial des phosphates et des engrais : "
    "marché boursier, agriculture, prix alimentaires, matières premières, "
    "actualités et performance financière d'OCP — modélisé selon l'approche "
    "Kimball (Star Schemas conformes autour de DimDate)."
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Navigation vers les dashboards
# ---------------------------------------------------------------------------

st.subheader("Dashboards disponibles")

dashboards = [
    {
        "page": "pages/Marche_Boursier.py",
        "label": "📈 Marché boursier",
        "desc": "FactStockPrices — cours OHLCV des concurrents cotés d'OCP (MOS, NTR, CF, ICL, YARIY). Grain : Entreprise + Jour.",
    },
    {
        "page": "pages/Production_Agricole.py",
        "label": "🌾 Production agricole",
        "desc": "FactCropProduction — production mondiale par pays / culture / année (FAOSTAT). Grain : Pays + Culture + Année + Élément.",
    },
    {
        "page": "pages/Indice_Prix_Alimentaire.py",
        "label": "🍞 Indice des prix alimentaires",
        "desc": "FactFoodPriceIndex — FAO Food Price Index et sous-indices (viande, lait, céréales, huiles, sucre). Grain : Mois.",
    },
    {
        "page": "pages/Matieres_Premieres.py",
        "label": "🏭 Matières premières",
        "desc": "FactCommodityPrices — prix mondiaux des phosphates et engrais (World Bank CMO). Grain : Matière première + Mois.",
    },
    {
        "page": "pages/Actualites.py",
        "label": "📰 Actualités",
        "desc": "FactNews — veille médiatique du secteur (OCP, phosphate, fertilizer, agriculture, concurrents). Grain : Article.",
    },
    {
        "page": "pages/Finances_OCP.py",
        "label": "🏦 Finances OCP",
        "desc": "FactOCPFinancials — chiffre d'affaires, EBITDA, marge, résultat net trimestriels d'OCP. Grain : Trimestre.",
    },
]

cols = st.columns(3)
for i, d in enumerate(dashboards):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{d['label']}**")
            st.caption(d["desc"])
            try:
                st.page_link(d["page"], label="Ouvrir →", icon="↗️")
            except Exception:
                # Anciennes versions de Streamlit : st.page_link indisponible
                st.info("Ouvre cette page depuis le menu latéral.")

st.markdown("---")

# ---------------------------------------------------------------------------
# État du Data Warehouse
# ---------------------------------------------------------------------------

st.subheader("🗄️ État du Data Warehouse")

try:
    counts_df = load_row_counts()
    kpi_cols = st.columns(len(counts_df))
    for col, (_, row) in zip(kpi_cols, counts_df.iterrows()):
        value = f"{int(row['rows']):,}" if pd.notna(row["rows"]) else "—"
        col.metric(label=row["table"], value=value)
except Exception as e:
    st.warning("Impossible de charger les volumes des tables de faits.")
    st.exception(e)

st.markdown("### 🩺 Dernière exécution ETL par source")
try:
    etl_df = load_last_etl_runs()
    if etl_df.empty:
        st.info("Aucune exécution ETL enregistrée pour le moment (EtlRunLog vide).")
    else:
        etl_display = etl_df.copy()
        etl_display["status"] = etl_display["status"].map(
            {"SUCCESS": "SUCCESS", "FAILED": "FAILED"}
        ).fillna(etl_display["status"])
        st.dataframe(etl_display, use_container_width=True, hide_index=True)
except Exception as e:
    st.warning(
        "Impossible de charger EtlRunLog. Vérifie que la table existe et que "
        "le pipeline ETL (run_etl.py) a déjà tourné au moins une fois."
    )
    st.exception(e)

st.markdown("---")
st.caption(f"OCP DataFlow · Actualisé le {datetime.now():%d/%m/%Y à %H:%M}")