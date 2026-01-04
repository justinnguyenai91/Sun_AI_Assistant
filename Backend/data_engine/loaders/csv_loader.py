import pandas as pd
import os

DATA_PATH = os.getenv("CSV_DATA_PATH", "data")

class CSVLoader:
    def load(self, table: str):
        path = f"{DATA_PATH}/{table}.csv"
        return pd.read_csv(path)
