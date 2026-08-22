"""
DAG trimestriel -- Communiqués officiels OCP Group (FactOCPFinancials)

Airflow ne propose pas de préset "@quarterly" natif : on utilise
l'expression cron équivalente (1er jour des mois 1, 4, 7, 10 à 6h).
"""
from datetime import datetime, timedelta
from functools import partial

from airflow import DAG
from airflow.operators.python import PythonOperator

from dags.common import run_source, load_and_log

from src.etl.extract.ocp_financials import OCPFinancialsCollector
from src.etl.transform import transform_ocp

with DAG(
    dag_id="dag_quarterly_financials",
    description="Communiqués officiels OCP Group (FactOCPFinancials)",
    schedule="0 6 1 1,4,7,10 *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=15)},
    tags=["ocp-dataflow", "quarterly"],
) as dag:

    extract_ocp = PythonOperator(
        task_id="extract_transform_validate_ocp_financials",
        python_callable=partial(
            run_source,
            name="OCPFinancialsCollector",
            collector_cls=OCPFinancialsCollector,
            transformer_module=transform_ocp,
            single_table_name="FactOCPFinancials",
        ),
    )

    load = PythonOperator(
        task_id="load_and_log",
        python_callable=load_and_log,
        op_kwargs={
            "source_task_ids": {
                "OCPFinancialsCollector": "extract_transform_validate_ocp_financials",
            }
        },
    )

    extract_ocp >> load