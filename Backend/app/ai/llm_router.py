from app.rules.decision_snapshot import DecisionSnapshot

def explain_decision(
    self,
    decision_snapshot: DecisionSnapshot,
    context: dict,
):
    """
    READ-ONLY explanation.
    LLM MUST NOT influence decision.
    """
    prompt = self.build_prompt(
        decision_snapshot=decision_snapshot,
        context=context,
    )
    return self.call_llm(prompt)
