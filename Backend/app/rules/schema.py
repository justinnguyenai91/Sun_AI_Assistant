from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass(frozen=True)
class RuleDecision:
    rule_id: str
    outcome: str
    score: float
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class DecisionResult:
    decisions: List[RuleDecision]
    final_outcome: str
