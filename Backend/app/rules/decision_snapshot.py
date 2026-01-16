from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class DecisionSnapshot:
    """
    Immutable snapshot of a decision.
    After creation, it MUST NOT change.
    """

    final_outcome: str
    decisions: List[Dict[str, Any]]
    metrics: Dict[str, Any]

    @staticmethod
    def from_decision(decision_result, metrics: Dict[str, Any]) -> "DecisionSnapshot":
        return DecisionSnapshot(
            final_outcome=decision_result.final_outcome,
            decisions=[
                {
                    "rule_id": d.rule_id,
                    "outcome": d.outcome,
                    "score": d.score,
                }
                for d in decision_result.decisions
            ],
            metrics=dict(metrics),  # shallow copy
        )
