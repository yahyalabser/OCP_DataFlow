import re
import pandas as pd
from pathlib import Path
from config.settings import output_dir_news
from .io_utils import load_json

def _clean_text(text: str) -> str:
   if not isinstance(text, str):
      return text
   text = re.sub(r"<[^>]+>", "", text)
   text = re.sub(r"&nbsp;|&amp;|&quot;", " ", text)
   text = re.sub(r"\s*\[\+\d+ chars\]$", "", text)
   text = re.sub(r"\s{2,}", " ", text) 
   text = re.sub(r"[\r\n]+", " ", text)
   return text.strip()

def clean(df: pd.DataFrame) -> pd.DataFrame:
   df["author"] = df["author"].fillna("Unknown")
   df["date"] = pd.to_datetime(df["date"])
   df["content"] = df["content"].apply(_clean_text)
   df["title"] = df["title"].apply(_clean_text)
   return df

def transform(df : pd.DataFrame) -> pd.DataFrame:
   bridge_df = df[["url", "keyword"]].drop_duplicates()
   news_df = df.drop_duplicates(subset=["url"], keep="first").drop(columns=["keyword"])
   return {"news": news_df, "bridge": bridge_df}

def run() -> pd.DataFrame:
   filepath = Path(output_dir_news) / "news_latest.json"
   if not filepath.exists():
      raise FileNotFoundError(f"Aucune donnée News trouvée dans {filepath}")

   all_rows = []
   raw = load_json(filepath)

   for keyword, articles in raw.items():
      if not articles:
         continue
      for article in articles:
         all_rows.append({
            "keyword": keyword,
            "date": article["publishedAt"],
            "source_name": article["source"]["name"],
            "url": article["url"],
            "title": article.get("title"),
            "author": article.get("author") or "Unknown",
            "content": article.get("content"),
         })

   df = pd.DataFrame(all_rows)
   df = clean(df)
   return transform(df)
