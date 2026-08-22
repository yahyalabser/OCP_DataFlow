"""
DAG quotidien -- Marché boursier (Alpha Vantage) + Actualités (NewsAPI)

Orchestration uniquement : la logique métier reste entièrement dans
src/etl/ (voir dags/common.py pour le détail du fonctionnement).
"""
from datetime import datetime, timedelta
from functools import partial

from airflow import DAG
from airflow.operators.python import PythonOperator

from dags.common import run_source, load_and_log

from src.etl.extract.alpha_vantage_collector import AlphaVantageCollector
from src.etl.extract.news_collector import NewsCollector
from src.etl.transform import transform_alpha, transform_news

with DAG(
    dag_id="dag_daily_market",
    description="Alpha Vantage (FactStockPrices) + NewsAPI (FactNews, BridgeArticleKeyword)",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["ocp-dataflow", "daily"],
) as dag:

    extract_alpha = PythonOperator(
        task_id="extract_transform_validate_alpha",
        python_callable=partial(
            run_source,
            name="AlphaVantageCollector",
            collector_cls=AlphaVantageCollector,
            transformer_module=transform_alpha,
        ),
    )

    extract_news = PythonOperator(
        task_id="extract_transform_validate_news",
        python_callable=partial(
            run_source,
            name="NewsCollector",
            collector_cls=NewsCollector,
            transformer_module=transform_news,
        ),
    )

    load = PythonOperator(
        task_id="load_and_log",
        python_callable=load_and_log,
        op_kwargs={
            "source_task_ids": {
                "AlphaVantageCollector": "extract_transform_validate_alpha",
                "NewsCollector": "extract_transform_validate_news",
            }
        },
    )

    [extract_alpha, extract_news] >> load