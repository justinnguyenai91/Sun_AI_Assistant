from typing import Any, Dict, Optional

from app.semantic.resolver import SemanticResolver
from app.data.datasource import DataSource
from app.data.query_compiler.base import QueryCompiler
from app.metrics.calculator import MetricCalculator
from app.rules.engine import RuleEngine
from app.ai.llm_router import LLMRouter
from app.rules.decision_snapshot import DecisionSnapshot

class AnalysisService:
    """
    AnalysisService is an orchestration layer.

    Responsibilities:
    - Coordinate semantic resolution
    - Compile execution plan
    - Fetch & normalize data
    - Compute metrics
    - Evaluate rules
    - (Optional) Ask LLM to EXPLAIN results

    MUST NOT:
    - Contain business logic
    - Decide KPI / rule / policy
    - Generate SQL
    - Let LLM influence decisions
    """

    def __init__(
        self,
        *,
        semantic_resolver: SemanticResolver,
        datasource: DataSource,
        query_compiler: QueryCompiler,
        metric_calculator: MetricCalculator,
        rule_engine: RuleEngine,
        llm_router: Optional[LLMRouter] = None,
    ):
        self.semantic_resolver = semantic_resolver
        self.datasource = datasource
        self.query_compiler = query_compiler
        self.metric_calculator = metric_calculator
        self.rule_engine = rule_engine
        self.llm_router = llm_router

    def run_analysis(
        self,
        semantic_request: Dict[str, Any],
        *,
        use_ai_explanation: bool = False,
        ai_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute full deterministic analysis pipeline.

        semantic_request:
            - High-level request referencing semantic layer
            - NO DB / NO KPI / NO RULE

        Returns:
            {
                "metrics": {...},
                "decision": DecisionResult,
                "explanation": Optional[str]
            }
        """

        # 1️⃣ Resolve semantic → abstract execution plan
        execution_plan = self.semantic_resolver.resolve(semantic_request)

        # 2️⃣ Compile plan → datasource-specific instructions
        compiled_query = self.query_compiler.compile(execution_plan)
        execution_plan["compiled"] = compiled_query

        # 3️⃣ Fetch raw data
        raw_records = self.datasource.fetch(execution_plan)

        # 4️⃣ Normalize data
        normalized_data = self.datasource.normalize(raw_records)

        # 5️⃣ Compute metrics (pure function)
        metrics = self.metric_calculator.compute(normalized_data)

        # 6️⃣ Evaluate rules (pure, deterministic)
        decision = self.rule_engine.evaluate(metrics)
        decision_snapshot = DecisionSnapshot.from_decision(
            decision_result=decision,
            metrics=metrics,
        )        
        # 7️⃣ OPTIONAL: AI explanation (READ-ONLY)
        explanation = None
        if use_ai_explanation and self.llm_router:
            explanation = self.llm_router.explain_decision(
                decision_snapshot=decision_snapshot,
                context=ai_context or {},
            )

        return {
            "metrics": metrics,
            "decision": decision,
            "explanation": explanation,
        }
