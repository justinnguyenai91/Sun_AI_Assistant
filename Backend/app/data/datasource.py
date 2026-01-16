from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List


class DataSource(ABC):
    """
    DataSource is a low-level data access abstraction.

    Responsibilities:
    - Connect to a physical data source
    - Execute an execution plan
    - Normalize raw output into canonical structure

    It MUST NOT:
    - Know business meaning of data
    - Know metrics or KPIs
    - Contain SQL or domain logic
    """

    @abstractmethod
    def connect(self) -> None:
        """Initialize underlying connection/session"""
        pass

    @abstractmethod
    def fetch(self, plan: Dict[str, Any]) -> Iterable[Any]:
        """
        Execute data retrieval based on execution plan.

        Plan is a STRUCTURAL CONTRACT produced by semantic.resolver.
        """
        pass

    @abstractmethod
    def normalize(self, records: Iterable[Any]) -> List[Dict[str, Any]]:
        """
        Normalize raw records into List[Dict[str, Any]]

        Output must be:
        - Flat
        - JSON serializable
        - Deterministic
        """
        pass
