import logging, os
from logging.handlers import RotatingFileHandler

def get_logger(name : str):
   os.makedirs("logs", exist_ok=True)

   logger = logging.getLogger(name)
   logger.setLevel(logging.DEBUG)

   if not logger.handlers:
      formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")

      file_handler = RotatingFileHandler(f"logs/{name}.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
      file_handler.setFormatter(formatter)
      logger.addHandler(file_handler)

      console_handler = logging.StreamHandler()
      console_handler.setFormatter(formatter)
      logger.addHandler(console_handler)

   return logger
