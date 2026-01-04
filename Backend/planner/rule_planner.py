from decision.decision_schema import Decision, Metric, OrderBy
import os

DEFAULT_DATASOURCE = os.getenv("DATA_SOURCE", "csv")

def plan(question: str) -> Decision:
    q = question.lower()

    # Lesson 6: rule-based
    if "top" in q and "revenue" in q:
        return Decision(
            datasource=DEFAULT_DATASOURCE,
            table="sales",
            metrics=[Metric(field="revenue", agg="sum")],
            group_by=["product"],
            order_by=OrderBy(field="revenue", direction="desc"),
            limit=3
        )

    raise ValueError("Question not supported in Lesson 6")
