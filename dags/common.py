"""
Fonctions utilitaires partagées par les DAGs Airflow d'OCP DataFlow.

Ce module ne contient AUCUNE logique métier : il orchestre uniquement les
fonctions déjà existantes dans src/etl/ (collect, transform, validate,
upsert), pour respecter la séparation logique métier / orchestration
décrite au chapitre 7 du rapport. Il reproduit, pour l'essentiel, ce que
fait déjà src/etl/main.py::_run_source() et run_pipeline(), mais découpé
en tâches Airflow.
"""
import pickle
import time
from pathlib import Path

import pandera.pandas as pa

from src.logger_config import get_logger
from src.etl.quality_checks import validate
from src.etl.load.load_dimensions import load_dimensions
from src.etl.load.load_facts import load_facts
from src.etl.monitoring import log_run

TMP_DIR = Path("/opt/airflow/data/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger("airflow_common")


def run_source(name: str, collector_cls, transformer_module, single_table_name: str | None = None) -> str:
    """
    Exécute Extract -> Transform -> Validate pour UNE source, comme le fait
    src/etl/main.py::_run_source() (mêmes règles d'isolation des échecs par table).

    Retourne le chemin d'un fichier pickle contenant :
      {"validated": {nom_table: DataFrame}, "failed": [noms_table_exclues]}
    Ce fichier est transmis au task de chargement via XCom (on ne fait
    transiter que le chemin, pas les DataFrames eux-mêmes, ce qu'XCom
    ne gère pas bien nativement).
    """
    collector = collector_cls()
    collector.collect()

    output = transformer_module.run()
    tables = output if isinstance(output, dict) else {single_table_name: output}

    validated = {}
    failed_tables = []
    for table_name, df in tables.items():
        try:
            validated[table_name] = validate(table_name, df)
        except pa.errors.SchemaErrors as e:
            logger.error(
                f"[{name}] Validation échouée pour '{table_name}' "
                f"({len(e.failure_cases)} ligne(s) en échec) : table exclue."
            )
            failed_tables.append(table_name)
        except Exception as e:
            logger.error(f"[{name}] Erreur de validation pour '{table_name}' : {e}")
            failed_tables.append(table_name)

    if not validated:
        raise RuntimeError(f"[{name}] Aucune table validée : échec total de la source.")
    if failed_tables:
        logger.warning(f"[{name}] Terminé partiellement : {failed_tables} exclue(s).")

    path = TMP_DIR / f"{name}.pkl"
    with open(path, "wb") as f:
        pickle.dump({"validated": validated, "failed": failed_tables}, f)
    return str(path)


def load_and_log(ti, source_task_ids: dict) -> None:
    """
    source_task_ids : {nom_source: task_id_du_task_extract_transform_validate}

    Récupère les tables validées de chaque source du DAG (via XCom), les
    fusionne, appelle une seule fois load_dimensions()/load_facts() -- comme
    le fait src/etl/main.py::run_pipeline() -- puis journalise le résultat
    de chaque source dans EtlRunLog.
    """
    merged: dict = {}
    per_source_rows: dict[str, int] = {}
    per_source_failed: dict[str, list] = {}
    start = time.time()

    for source_name, task_id in source_task_ids.items():
        pickle_path = ti.xcom_pull(task_ids=task_id)
        with open(pickle_path, "rb") as f:
            payload = pickle.load(f)

        validated_tables = payload["validated"]
        per_source_failed[source_name] = payload["failed"]
        per_source_rows[source_name] = sum(len(df) for df in validated_tables.values())
        merged.update(validated_tables)

    dim_results = load_dimensions(merged)
    fact_results = load_facts(merged)
    duration = time.time() - start

    load_failed_tables = set(dim_results["failed"]) | set(fact_results["failed"])
    any_hard_failure = False

    for source_name in source_task_ids:
        validation_failed = bool(per_source_failed[source_name])
        if load_failed_tables:
            status = "FAILED"
            any_hard_failure = True
        elif validation_failed:
            status = "PARTIAL"
        else:
            status = "SUCCESS"

        log_run(
            source=source_name,
            rows_extracted=per_source_rows[source_name],
            rows_loaded=per_source_rows[source_name] if status != "FAILED" else 0,
            duration_seconds=duration,
            status=status,
            error_message=f"Tables exclues : {per_source_failed[source_name]}" if per_source_failed[source_name] else None,
        )

    if any_hard_failure:
        raise RuntimeError(f"Échec du chargement en base pour les tables : {load_failed_tables}")