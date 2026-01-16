from typing import List
from .schema import RuleDefinition, SemanticConfig


class SemanticRegistry:
    """
    Central lookup registry
    NO business logic
    """

    def __init__(self, config: SemanticConfig):
        self._rules_by_metric = self._index_rules(config.rules)

    @staticmethod
    def _index_rules(rules: List[RuleDefinition]):
        index = {}
        for rule in rules:
            index.setdefault(rule.applies_to, []).append(rule)
        return index

    def get_rules_for_metric(self, metric_name: str) -> List[RuleDefinition]:
        return self._rules_by_metric.get(metric_name, [])
