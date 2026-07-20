import logging, os

def get_logger(name : str):
   os.makedirs("logs", exist_ok=True)

   logger = logging.getLogger(name)
   logger.setLevel(logging.DEBUG)

   if not logger.handlers:   # évite les doublons si get_logger() est appelée plusieurs fois
      formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")

   # Sortie fichier
      file_handler = logging.FileHandler(f"logs/{name}.log", mode="a")
      file_handler.setFormatter(formatter)
      logger.addHandler(file_handler)

      # Sortie terminal
      console_handler = logging.StreamHandler()
      console_handler.setFormatter(formatter)
      logger.addHandler(console_handler)

   return logger
