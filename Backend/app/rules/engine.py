from app.rules.schema import DecisionResult, RuleDecision


class RuleEngine:
    def evaluate(self, metrics: dict) -> DecisionResult:
        decisions = []

        for rule in self.rules:
            result = rule.evaluate(metrics)
            decisions.append(
                RuleDecision(
                    rule_id=rule.id,
                    outcome=result.outcome,
                    score=result.score,
                    metadata=result.metadata
                )
            )

        final = self.policy.resolve(decisions)

        return DecisionResult(
            decisions=decisions,
            final_outcome=final
        )
