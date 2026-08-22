import sys
from src.etl.main import run_pipeline

if __name__ == "__main__":
   output = run_pipeline()
   results = output["results"]
   dim_results = output["dim_results"]
   fact_results = output["fact_results"]

   load_failed = bool(dim_results["failed"]) or bool(fact_results["failed"])

   if load_failed:
      print(
         f"Échec de chargement -- dimensions en échec : {dim_results['failed']} | "
         f"faits en échec : {fact_results['failed']}",
         file=sys.stderr,
      )

   if results["failed"] or load_failed:
      sys.exit(1)
   if results["partial"]:
      sys.exit(2)