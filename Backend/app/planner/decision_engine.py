from typing import Any, Dict

from .domain_registry import get_registry
from .query_builder import QueryBuilder


class DecisionEngine:
    """
    Translate semantic plan into an execution plan for the data adapter.
    """

    def decide(self, semantic_plan: Dict[str, Any]) -> Dict[str, Any]:
        raw_query = semantic_plan.get("raw_query") or ""
        raw_lc = str(raw_query).lower()
        params = dict(semantic_plan.get("params") or {})

        registry = get_registry()

        # -----------------------------
        # Metrics (if present) help disambiguate entity selection
        # -----------------------------
        metrics = params.pop("metrics", None)
        if isinstance(metrics, str) and metrics.strip():
            metrics = [metrics.strip()]
        if not isinstance(metrics, list):
            metrics = None
        else:
            metrics = [str(m).strip() for m in metrics if str(m).strip()] or None

        inferred_entity = None
        if metrics:
            for mid in metrics:
                ent = registry.metric_entity(mid)
                if ent:
                    inferred_entity = ent
                    break

        # -----------------------------
        # Canonicalize entity and action
        # -----------------------------
        # LLM entity can be wrong (e.g., "date"); use combined text + fallback to metrics.
        entity_text = f"{semantic_plan.get('entity') or ''} {raw_query}".strip()
        entity = registry.canonical_entity(entity_text, fallback=None)
        if not entity:
            entity = inferred_entity

        # intent from upstream (LLM/parser) is treated as action-like
        action_text = semantic_plan.get("intent") or raw_query
        action = registry.canonical_action(str(action_text), fallback="statistic")

        # Map high-level report intent to statistic templates
        if action == "report":
            action = "statistic"

        # -----------------------------
        # Group-by from semantic params
        # -----------------------------
        group_by = params.pop("group_by", None)
        order_by = params.pop("order_by", None)
        if not group_by:
            group_by = registry.parse_group_by(raw_query)

        # normalize group_by into None | str | list
        if isinstance(group_by, list):
            group_by = [str(x).strip() for x in group_by if str(x).strip()]
        elif isinstance(group_by, str):
            group_by = group_by.strip() or None
        else:
            group_by = None

        if not entity:
            return {"action": "noop", "entity": None, "filters": params, "group_by": group_by, "viz": None}

        # -----------------------------
        # Build execution plan (config-driven)
        # -----------------------------
        plan: Dict[str, Any] = {
            "entity": entity,
            "action": action,
            "filters": params,
            "group_by": group_by,
            "order_by": order_by,
            "metrics": metrics,
        }

        # Auth is not a filter; keep it separate to avoid leaking to query params/logging.
        auth = semantic_plan.get("auth")
        if isinstance(auth, dict) and auth:
            plan["auth"] = auth

        qb = QueryBuilder()
        plan = qb.build(plan)

        # Provide a reasonable default viz if template didn't set it
        if not plan.get("viz"):
            # tables for raw queries, bar for aggregations
            plan["viz"] = "table" if plan.get("group_by") in (None, "", []) else "bar"

        return plan
