import json

def load_json(filepath: str) -> dict | list:
   with open(filepath, "r", encoding="utf-8") as f:
      return json.load(f)
