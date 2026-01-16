import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.data.datasource import DataSource


class CSVSource(DataSource):
    def __init__(self, config: Dict[str, Any]):
        """
        config:
        {
            "path": "/data/orders.csv",
            "delimiter": ","
        }
        """
        self.path = Path(config["path"])
        self.delimiter = config.get("delimiter", ",")
        self._connected = False

    def connect(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"CSV not found: {self.path}")
        self._connected = True

    def fetch(self, plan: Dict[str, Any]) -> Iterable[Any]:
        if not self._connected:
            self.connect()

        with self.path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            for row in reader:
                yield row

    def normalize(self, records: Iterable[Any]) -> List[Dict[str, Any]]:
        return [dict(r) for r in records]
