import sys
from src.etl.main import run_pipeline

if __name__ == "__main__":
   output = run_pipeline()
   results = output["results"]

   if results["failed"]:
      sys.exit(1)
   if results["partial"]:
      sys.exit(2)