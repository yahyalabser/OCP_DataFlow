"""
DAG mensuel -- FAO Food Price Index (FFPI) + World Bank CMO (matières premières)

Orchestration uniquement : la logique métier reste entièrement dans
src/etl/ (voir dags/common.py pour le détail du fonctionnement).
"""
from datetime import datetime, timedelta
from functools import partial

from airflow import DAG
from airflow.operators.python import PythonOperator

from dags.common import run_source, load_and_log

from src.etl.extract.ffpi_collector import FFPICollector
from src.etl.extract.world_bank_collector import WorldBankCollector
from src.etl.transform import transform_ffpi, transform_worldbank

with DAG(
    dag_id="dag_monthly_prices",
    description="FAO Food Price Index (FactFoodPriceIndex) + World Bank CMO (FactCommodityPrices)",
    schedule="@monthly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["ocp-dataflow", "monthly"],
) as dag:

    extract_ffpi = PythonOperator(
        task_id="extract_transform_validate_ffpi",
        python_callable=partial(
            run_source,
            name="FFPICollector",
            collector_cls=FFPICollector,
            transformer_module=transform_ffpi,
            single_table_name="FactFoodPriceIndex",
        ),
    )

    extract_worldbank = PythonOperator(
        task_id="extract_transform_validate_worldbank",
        python_callable=partial(
            run_source,
            name="WorldBankCollector",
            collector_cls=WorldBankCollector,
            transformer_module=transform_worldbank,
        ),
    )

    load = PythonOperator(
        task_id="load_and_log",
        python_callable=load_and_log,
        op_kwargs={
            "source_task_ids": {
                "FFPICollector": "extract_transform_validate_ffpi",
                "WorldBankCollector": "extract_transform_validate_worldbank",
            }
        },
    )

    [extract_ffpi, extract_worldbank] >> load