"""
DAG annuel -- FAOSTAT (production agricole mondiale, FactCropProduction)
"""
from datetime import datetime, timedelta
from functools import partial

from airflow import DAG
from airflow.operators.python import PythonOperator

from dags.common import run_source, load_and_log

from src.etl.extract.fao_collector import FAOCollector
from src.etl.transform import transform_fao

with DAG(
    dag_id="dag_annual_agri",
    description="FAOSTAT -- production agricole mondiale (FactCropProduction)",
    schedule="@yearly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=15)},
    tags=["ocp-dataflow", "yearly"],
) as dag:

    extract_fao = PythonOperator(
        task_id="extract_transform_validate_fao",
        python_callable=partial(
            run_source,
            name="FAOCollector",
            collector_cls=FAOCollector,
            transformer_module=transform_fao,
        ),
    )

    load = PythonOperator(
        task_id="load_and_log",
        python_callable=load_and_log,
        op_kwargs={
            "source_task_ids": {
                "FAOCollector": "extract_transform_validate_fao",
            }
        },
    )

    extract_fao >> load