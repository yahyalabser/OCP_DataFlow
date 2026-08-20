from src.config.db_config import get_engine
from src.logger_config import get_logger
from sqlalchemy import text

logger = get_logger("monitoring")

def log_run(source: str, rows_extracted: int, rows_loaded: int, duration_seconds: float, status: str, error_message: str = None):
   """
   Insère un journal d'exécution ETL dans la table "EtlRunLog" en utilisant SQLAlchemy.
   """
   engine = get_engine()
    
   requete_sql = text("""
      INSERT INTO ocp_dataflow."EtlRunLog" 
      (source, rows_extracted, rows_loaded, duration_seconds, status, error_message) 
      VALUES (:source, :rows_extracted, :rows_loaded, :duration_seconds, :status, :error_message)
      RETURNING run_id, run_datetime;
   """)
    
   parametres = {
      "source": source,
      "rows_extracted": rows_extracted,
     "rows_loaded": rows_loaded,
      "duration_seconds": duration_seconds,
      "status": status,
      "error_message": error_message
   }
    
   try:
      with engine.begin() as connection:
         result = connection.execute(requete_sql, parametres)
         row = result.fetchone()
         if row:
            print(f"Log inséré avec succès ! (ID: {row.run_id}, Date: {row.run_datetime})")
                
   except Exception as erreur:
      logger.error(f"Erreur lors de l'insertion du log ETL : {erreur}", exc_info=True)