from typing import Any, Dict, Iterable, List
import requests

from app.data.datasource import DataSource


class MESSource(DataSource):
    def __init__(self, config: Dict[str, Any]):
        self.endpoint = config["endpoint"]
        self.token = config["token"]
        self.session = None

    def connect(self) -> None:
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })

    def fetch(self, plan: Dict[str, Any]) -> Iterable[Any]:
        self.connect()

        response = self.session.post(self.endpoint, json=plan)
        response.raise_for_status()

        for item in response.json().get("data", []):
            yield item

    def normalize(self, records: Iterable[Any]) -> List[Dict[str, Any]]:
        return [dict(r) for r in records]
