import pandas as pd
from sqlalchemy import create_engine
import os

class PostgresLoader:
    def __init__(self):
        conn_str = os.getenv("POSTGRES_CONN")
        self.engine = create_engine(conn_str)

    def load(self, table: str):
        return pd.read_sql(f"SELECT * FROM {table}", self.engine)
