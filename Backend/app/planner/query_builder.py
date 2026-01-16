import os
from typing import Dict, Any, Optional
import logging

try:
    import yaml
except Exception:
    yaml = None

logger = logging.getLogger(__name__)


class QueryBuilder:
    _templates = None

    def __init__(self, templates_path: Optional[str] = None):
        if templates_path:
            self.templates_path = templates_path
        else:
            self.templates_path = os.path.join(os.path.dirname(__file__), "..", "config", "templates.yaml")

        if QueryBuilder._templates is None:
            QueryBuilder._templates = self._load_templates()

    def _load_templates(self):
        if yaml is None:
            logger.warning("PyYAML not available; templates cannot be loaded from YAML")
            return []
        try:
            with open(self.templates_path, "r", encoding="utf-8") as f:
                doc = yaml.safe_load(f)
                return doc.get("templates", []) if isinstance(doc, dict) else []
        except Exception as e:
            logger.exception("Failed to load templates: %s", e)
            return []

    def find_template(self, entity: str, action: str, group_by: Optional[str]):
        return self.find_template_with_metrics(entity=entity, action=action, group_by=group_by, metrics=None)

    def get_template_by_id(self, template_id: str | None):
        if not template_id:
            return None
        for t in QueryBuilder._templates or []:
            if t.get("id") == template_id:
                return t
        return None

    def find_template_with_metrics(self, entity: str, action: str, group_by: Optional[str], metrics: Optional[list[str]]):
        def normalize_gb(gb):
            if gb is None:
                return None
            # accept list, comma-separated string, or single string
            if isinstance(gb, list):
                parts = [str(x).strip() for x in gb if x]
                return tuple(sorted(parts)) if parts else None
            if isinstance(gb, str):
                if "," in gb:
                    parts = [p.strip() for p in gb.split(",") if p.strip()]
                    return tuple(sorted(parts)) if parts else None
                return (gb.strip(),)
            return None

        requested = normalize_gb(group_by)

        requested_metrics = None
        if isinstance(metrics, list):
            requested_metrics = [str(m).strip() for m in metrics if str(m).strip()]
            if not requested_metrics:
                requested_metrics = None

        def provides_requested(tpl: dict) -> bool:
            if not requested_metrics:
                return True
            provides = tpl.get("provides")
            if not isinstance(provides, list) or not provides:
                return False
            provides_set = {str(x).strip() for x in provides if str(x).strip()}
            # if any requested metric is provided, consider it a match (planner can request 1 primary metric)
            return any(m in provides_set for m in requested_metrics)

        # prefer exact (order-insensitive) match on group_by
        for t in QueryBuilder._templates or []:
            if t.get("entity") == entity and t.get("action") == action:
                tpl_gb = normalize_gb(t.get("group_by"))
                if tpl_gb is not None and requested is not None and tpl_gb == requested and provides_requested(t):
                    return t

        # fallback: prefer templates with no group_by (generic)
        for t in QueryBuilder._templates or []:
            if t.get("entity") == entity and t.get("action") == action:
                if (t.get("group_by") in (None, "", []) or normalize_gb(t.get("group_by")) is None) and provides_requested(t):
                    return t

        # last fallback: any template matching entity+action
        for t in QueryBuilder._templates or []:
            if t.get("entity") == entity and t.get("action") == action:
                if not provides_requested(t):
                    continue
                return t
        return None

    def build(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        # enrich execution_plan in-place and return it
        entity = execution_plan.get("entity") or execution_plan.get("target")
        action = execution_plan.get("action")
        group_by = execution_plan.get("group_by")
        metrics = execution_plan.get("metrics")

        # Allow forcing a template_id (used by computed templates to run steps)
        forced = execution_plan.get("template_id")
        template = self.get_template_by_id(forced) if forced else None

        if template is None:
            template = self.find_template_with_metrics(entity, action, group_by, metrics=metrics)
        if template:
            execution_plan["template_id"] = template.get("id")
            execution_plan["adapter"] = template.get("adapter")
            execution_plan.setdefault("aggregates", template.get("aggregates", []))
            # extended template schema support
            if template.get("type"):
                execution_plan.setdefault("type", template.get("type"))
            if template.get("provides"):
                execution_plan.setdefault("provides", template.get("provides"))
            if template.get("steps"):
                execution_plan.setdefault("steps", template.get("steps"))
            if template.get("formula"):
                execution_plan.setdefault("formula", template.get("formula"))
            if template.get("fixed_params"):
                execution_plan.setdefault("fixed_params", template.get("fixed_params"))
            if template.get("query_params"):
                execution_plan.setdefault("query_params", template.get("query_params"))
            if template.get("dimension_fields"):
                execution_plan.setdefault("dimension_fields", template.get("dimension_fields"))
            if template.get("dimension_defaults"):
                execution_plan.setdefault("dimension_defaults", template.get("dimension_defaults"))
            if template.get("measure"):
                execution_plan.setdefault("measure", template.get("measure"))
            # Optional routing and contract fields
            if template.get("method"):
                execution_plan.setdefault("method", template.get("method"))
            if template.get("endpoint"):
                execution_plan.setdefault("endpoint", template.get("endpoint"))
            if template.get("params"):
                execution_plan.setdefault("params", template.get("params"))
            if template.get("viz"):
                execution_plan.setdefault("viz", template.get("viz"))

        # convert time_range slot to explicit from/to params for adapters
        filters = execution_plan.get("filters") or {}
        tr = filters.get("time_range")
        if tr:
            from_to = self._time_range_to_from_to(tr)
            if from_to:
                filters.update(from_to)
                # remove time_range to avoid duplication
                filters.pop("time_range", None)

        # ------------------------------------------------------------
        # Default: production-result actual should use FINAL output
        # If the user doesn't ask for workstation-level detail, use:
        #   finalYn = Y and reflect = Y
        # so KPIs like defect PPM and plan achievement use end-of-line output.
        # ------------------------------------------------------------
        try:
            tpl_id = (template or {}).get("id")
            is_prod_actual_details = tpl_id in (
                "prod.result.actual.daily",
                "prod.result.actual.daily_shift",
            )

            if is_prod_actual_details:
                # Detect workstation/detail intent: process filters or group-by on process
                gb = execution_plan.get("group_by")
                gb_list = gb if isinstance(gb, list) else ([gb] if isinstance(gb, str) and gb.strip() else [])
                gb_norm = {str(x).strip() for x in gb_list if str(x).strip()}
                wants_workstation_detail = (
                    "process" in gb_norm
                    or "processType" in gb_norm
                    or "process_type" in gb_norm
                    or bool(filters.get("processPks"))
                )

                # Only apply defaults if user didn't explicitly set flags.
                if not wants_workstation_detail:
                    if not str(filters.get("finalYn") or "").strip():
                        filters["finalYn"] = "Y"
                    if not str(filters.get("reflect") or "").strip():
                        filters["reflect"] = "Y"
        except Exception:
            # Never block query execution on defaulting logic
            pass

        execution_plan["filters"] = filters
        return execution_plan

    def _time_range_to_from_to(self, tr) -> Optional[Dict[str, str]]:
        from datetime import date, timedelta, datetime
        try:
            # dict with explicit from/to
            if isinstance(tr, dict):
                if tr.get("from") and tr.get("to"):
                    # ensure isoformat strings
                    try:
                        _f = datetime.fromisoformat(str(tr.get("from")))
                        _t = datetime.fromisoformat(str(tr.get("to")))
                        return {"from": _f.date().isoformat(), "to": _t.date().isoformat()}
                    except Exception:
                        # fallthrough to other handlers
                        pass
                # structured {value, unit}
                val = tr.get("value")
                unit = tr.get("unit", "").lower()
                today = date.today()
                if unit.startswith("year") and isinstance(val, int):
                    from_date = today - timedelta(days=365 * val)
                    return {"from": from_date.isoformat(), "to": today.isoformat()}
                if unit.startswith("month") and isinstance(val, int):
                    from_date = today - timedelta(days=30 * val)
                    return {"from": from_date.isoformat(), "to": today.isoformat()}

            # string: ISO range like '2024-01-01/2024-01-31' or single ISO date
            if isinstance(tr, str):
                if "/" in tr:
                    parts = tr.split("/", 1)
                    try:
                        f = datetime.fromisoformat(parts[0].strip()).date()
                        t = datetime.fromisoformat(parts[1].strip()).date()
                        return {"from": f.isoformat(), "to": t.isoformat()}
                    except Exception:
                        pass
                # '1_years' legacy support
                if tr.endswith("_years"):
                    try:
                        years = int(tr.split("_")[0])
                        today = date.today()
                        from_date = today - timedelta(days=365 * years)
                        return {"from": from_date.isoformat(), "to": today.isoformat()}
                    except Exception:
                        pass
                # single ISO date -> treat as from=<date> to=<date>
                try:
                    d = datetime.fromisoformat(tr.strip()).date()
                    return {"from": d.isoformat(), "to": d.isoformat()}
                except Exception:
                    pass
        except Exception:
            logger.exception("Failed to convert time_range: %s", tr)
        return None
