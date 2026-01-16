from typing import Dict, Any
from semantic.schema import SemanticRule
from .schema import RuleEvaluationResult


class RuleEvaluator:
    OPERATORS = {
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }

    def evaluate(
        self,
        rule: SemanticRule,
        facts: Dict[str, Any],
    ) -> RuleEvaluationResult:
        left = facts.get(rule.applies_to)
        right = facts.get(rule.condition["right"])

        if left is None or right is None:
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                matched=False,
                decision=None,
                reason=None,
                context=facts,
            )

        op = self.OPERATORS.get(rule.condition["operator"])
        matched = op(left, right) if op else False

        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            matched=matched,
            decision=rule.decision if matched else None,
            reason=rule.reason if matched else None,
            context=facts,
        )
