from abc import ABC, abstractmethod
from typing import Dict, Any


class QueryCompiler(ABC):
    """
    Compile abstract ExecutionPlan into
    datasource-specific query instructions.
    """

    @abstractmethod
    def compile(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        pass
