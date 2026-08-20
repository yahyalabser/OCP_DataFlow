"""
Dashboard exploratoire — FactNews (OCP DataFlow)
====================================================

Objectif : valider que le modèle dimensionnel (DimDate, DimNewsSource,
DimKeyword, BridgeArticleKeyword, FactNews) répond à la question métier :
« Quelles actualités récentes concernent le secteur des phosphates et
OCP, et à quelle fréquence en parle-t-on ? »

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

st.set_page_config(page_title="OCP DataFlow — Actualités", page_icon="📰", layout="wide")

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
def load_keywords() -> pd.DataFrame:
    return pd.read_sql('SELECT keyword FROM ocp_dataflow."DimKeyword" ORDER BY keyword;', get_engine())


@st.cache_data(ttl=600)
def load_sources() -> pd.DataFrame:
    return pd.read_sql(
        'SELECT source_name FROM ocp_dataflow."DimNewsSource" ORDER BY source_name;', get_engine()
    )


@st.cache_data(ttl=600)
def load_news(keywords: list[str], source_names: list[str], start: date, end: date) -> pd.DataFrame:
    if not (keywords and source_names):
        return pd.DataFrame()
    query = """
        SELECT
            n.url, n.full_date, n.published_at, n.source_name, n.title, n.author, b.keyword
        FROM ocp_dataflow."FactNews" n
        JOIN ocp_dataflow."BridgeArticleKeyword" b ON b.url = n.url
        WHERE b.keyword = ANY(%(keywords)s)
          AND n.source_name = ANY(%(source_names)s)
          AND n.full_date BETWEEN %(start)s AND %(end)s
        ORDER BY n.full_date DESC;
    """
    return pd.read_sql(
        query, get_engine(),
        params={"keywords": keywords, "source_names": source_names, "start": start, "end": end},
    )


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("📰 Veille médiatique — Secteur des phosphates")
st.caption("Domaine : News — Table de faits : FactNews — Grain : Article (mots-clés via BridgeArticleKeyword)")

try:
    keywords_df = load_keywords()
    sources_df = load_sources()
except Exception as e:
    st.error(
        "Impossible de se connecter à la base PostgreSQL. "
        "Vérifie les variables POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD."
    )
    st.exception(e)
    st.stop()

if keywords_df.empty or sources_df.empty:
    st.warning("Dimensions vides (DimKeyword / DimNewsSource). As-tu déjà lancé le pipeline ETL NewsAPI ?")
    st.stop()

# --- Filtres (sidebar) ---
st.sidebar.header("Filtres")
selected_keywords = st.sidebar.multiselect(
    "Mots-clés", options=keywords_df["keyword"].tolist(), default=keywords_df["keyword"].tolist(),
)
selected_sources = st.sidebar.multiselect(
    "Sources", options=sources_df["source_name"].tolist(), default=sources_df["source_name"].tolist(),
)
today = date.today()
start_date, end_date = st.sidebar.date_input("Période", value=(today - timedelta(days=90), today))

if not (selected_keywords and selected_sources):
    st.info("Sélectionne au moins un mot-clé et une source dans le panneau de gauche.")
    st.stop()

df = load_news(selected_keywords, selected_sources, start_date, end_date)

if df.empty:
    st.warning("Aucun article sur cette période pour ces filtres.")
    st.stop()

# Un même article peut être lié à plusieurs mots-clés (table de pont) :
# on déduplique par url (clé métier de l'article) pour les décomptes
# globaux, pour ne pas fausser les indicateurs de volume de presse.
articles_df = df.drop_duplicates(subset="url")

# --- KPIs ---
st.subheader("Aperçu")
kpi_cols = st.columns(3)
kpi_cols[0].metric("Articles uniques", f"{articles_df['url'].nunique():,}")
kpi_cols[1].metric("Sources distinctes", f"{articles_df['source_name'].nunique():,}")
kpi_cols[2].metric("Mots-clés distincts", f"{df['keyword'].nunique():,}")

# --- Volume d'articles dans le temps ---
st.subheader("Volume d'articles dans le temps")
volume_df = articles_df.groupby("full_date", as_index=False)["url"].nunique().rename(
    columns={"url": "articles"}
)
fig_volume = px.bar(
    volume_df, x="full_date", y="articles", labels={"full_date": "Date", "articles": "Nombre d'articles"},
)
st.plotly_chart(fig_volume, use_container_width=True)

# --- Top mots-clés / sources ---
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Top mots-clés")
    kw_counts = (
        df.groupby("keyword", as_index=False)["url"].nunique()
        .rename(columns={"url": "articles"})
        .sort_values("articles", ascending=False).head(15)
    )
    fig_kw = px.bar(
        kw_counts, x="articles", y="keyword", orientation="h",
        labels={"articles": "Articles", "keyword": "Mot-clé"},
    )
    fig_kw.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_kw, use_container_width=True)

with col_right:
    st.subheader("Top sources")
    src_counts = (
        articles_df.groupby("source_name", as_index=False)["url"].nunique()
        .rename(columns={"url": "articles"})
        .sort_values("articles", ascending=False).head(15)
    )
    fig_src = px.bar(
        src_counts, x="articles", y="source_name", orientation="h",
        labels={"articles": "Articles", "source_name": "Source"},
    )
    fig_src.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_src, use_container_width=True)

# --- Table brute ---
with st.expander("Voir les articles"):
    st.dataframe(
        articles_df[["full_date", "source_name", "title", "author", "url"]].sort_values("full_date", ascending=False),
        use_container_width=True,
        column_config={"url": st.column_config.LinkColumn("Lien")},
    )
    st.download_button(
        "Télécharger en CSV",
        articles_df.to_csv(index=False).encode("utf-8"),
        file_name="fact_news_export.csv",
        mime="text/csv",
    )
