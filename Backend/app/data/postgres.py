from typing import Any, Dict, Iterable, List, Optional

import psycopg2
import psycopg2.extras

from app.data.datasource import DataSource


class PostgresSource(DataSource):
    def __init__(self, config: Dict[str, Any]):
        """
        config:
        {
            "dsn": "dbname=mes user=readonly password=*** host=10.0.0.1"
        }
        """
        self.dsn = config["dsn"]
        self.conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> None:
        if self.conn is None:
            self.conn = psycopg2.connect(self.dsn)

    def fetch(self, plan: Dict[str, Any]) -> Iterable[Any]:
        """
        SQL is NOT defined here.
        It must be injected into plan by resolver/compiler.
        """
        self.connect()

        compiled = plan.get("compiled")
        if not compiled:
            raise ValueError("ExecutionPlan missing compiled query")

        sql = compiled.get("sql")
        params = compiled.get("params", {})

        if not sql:
            raise ValueError("Compiled query missing SQL")

        with self.conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                yield row

    def normalize(self, records: Iterable[Any]) -> List[Dict[str, Any]]:
        return [dict(r) for r in records]
