import sys
from etl.main import run_pipeline

if __name__ == "__main__":
   output = run_pipeline()
   results = output["results"]
   print(results)
   if results["failed"]:
      sys.exit(1)
   print(list(output["data"].keys()))
