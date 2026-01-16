from typing import List, Optional
from app.rules.schema import RuleEvaluationResult, DecisionResult


class DecisionPolicy:
    """
    Aggregate rule evaluations → final decision
    """

    PRIORITY = ["CRITICAL", "WARNING", "OK"]

    def decide(
        self,
        evaluations: List[RuleEvaluationResult],
        facts: dict,
    ) -> Optional[DecisionResult]:
        matched = [e for e in evaluations if e.matched]

        if not matched:
            return None

        matched.sort(
            key=lambda e: self.PRIORITY.index(e.decision)
        )

        winner = matched[0]

        return DecisionResult(
            decision=winner.decision,
            reason=winner.reason,
            source="RULE",
            matched_rules=[e.rule_id for e in matched],
            facts=facts,
        )
