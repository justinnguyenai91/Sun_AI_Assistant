import logging
import os
import copy
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from . import lookup


def _safe_get_path(obj: Any, path: str):
    if obj is None or not path:
        return None
    cur = obj
    for part in str(path).split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _safe_number(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        s = str(v).strip().replace(",", "")
        if not s:
            return None
        return float(s)
    except Exception:
        return None


def _safe_eval_formula(formula: str, variables: Dict[str, Any]) -> float | None:
    """Safely evaluate a simple arithmetic formula using provided variables.

    Supported: +, -, *, /, parentheses, numeric literals, variable names.
    """
    import ast
    import operator as op

    if not isinstance(formula, str) or not formula.strip():
        return None

    allowed_ops = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.USub: op.neg,
        ast.UAdd: op.pos,
    }

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Num):
            return float(node.n)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            v = variables.get(node.id)
            return float(v) if isinstance(v, (int, float)) else (float(v) if _safe_number(v) is not None else 0.0)
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            left = _eval(node.left)
            right = _eval(node.right)
            try:
                return allowed_ops[type(node.op)](left, right)
            except ZeroDivisionError:
                return None
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported expression")

    try:
        tree = ast.parse(formula, mode="eval")
        return _eval(tree)
    except Exception:
        return None


def _load_ontology_metrics() -> Dict[str, Any]:
    try:
        import yaml
    except Exception:
        yaml = None

    if yaml is None:
        return {}

    path = os.path.join(os.path.dirname(__file__), "..", "config", "ontology.yaml")
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        metrics = doc.get("metrics")
        return metrics if isinstance(metrics, dict) else {}
    except Exception:
        return {}


def _is_computed_metric(metric_def: Any) -> bool:
    return isinstance(metric_def, dict) and isinstance(metric_def.get("formula"), str) and bool(metric_def.get("formula").strip())


def _resolve_metric_dependencies(requested: list[str], metrics_cfg: Dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return (base_metrics, computed_metrics) needed for requested metrics."""
    base: list[str] = []
    computed: list[str] = []

    seen: set[str] = set()

    def visit(metric_id: str):
        mid = str(metric_id).strip()
        if not mid or mid in seen:
            return
        seen.add(mid)

        mdef = metrics_cfg.get(mid) if isinstance(metrics_cfg, dict) else None
        if _is_computed_metric(mdef):
            deps = mdef.get("depends_on") or []
            if isinstance(deps, list):
                for d in deps:
                    visit(str(d))
            if mid not in computed:
                computed.append(mid)
        else:
            if mid not in base:
                base.append(mid)

    for m in requested or []:
        visit(m)

    return base, computed


logger = logging.getLogger(__name__)


class Planner:
    """
    Planner orchestrates execution flow:
    request -> semantic -> decision -> data -> response

    - No business logic
    - No KPI knowledge
    - No SQL
    """

    def __init__(
        self,
        semantic_resolver,
        decision_engine,
        data_adapter,
    ):
        self.semantic_resolver = semantic_resolver
        self.decision_engine = decision_engine
        self.data_adapter = data_adapter

    @staticmethod
    def _redact_for_log(obj: Any) -> Any:
        """Best-effort redaction for logs (never include tokens)."""
        try:
            if isinstance(obj, dict):
                out: Dict[str, Any] = {}
                for k, v in obj.items():
                    key = str(k)
                    key_lc = key.lower()

                    # Always redact auth blocks.
                    if key_lc == "auth":
                        out[key] = {"redacted": True}
                        continue

                    # Common token keys (context or otherwise).
                    if key_lc in ("mestoken", "mes_token", "externalapitoken", "external_api_token", "token"):
                        out[key] = "***"
                        continue

                    if isinstance(v, dict):
                        out[key] = Planner._redact_for_log(v)
                    elif isinstance(v, list):
                        out[key] = [Planner._redact_for_log(x) for x in v]
                    else:
                        out[key] = v
                return out
            if isinstance(obj, list):
                return [Planner._redact_for_log(x) for x in obj]
        except Exception:
            return {"redacted": True}
        return obj

    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration entrypoint.
        """

        logger.info("Planner.start", extra={"request": self._redact_for_log(request)})

        # Multi-factory execution: run the same request per factory and merge.
        ctx = request.get("context") if isinstance(request, dict) else None
        if not isinstance(ctx, dict):
            ctx = {}

        raw_codes = ctx.get("factoryCodes")
        codes: list[str] = []
        if isinstance(raw_codes, str):
            # e.g. "FAC01, DJVN1"
            parts = [p.strip() for p in raw_codes.replace(";", ",").split(",")]
            codes = [p for p in parts if p]
        elif isinstance(raw_codes, list):
            for x in raw_codes:
                s = str(x).strip()
                if s:
                    codes.append(s)

        # de-dup, preserve order
        seen: set[str] = set()
        codes = [c for c in codes if not (c in seen or seen.add(c))]

        if len(codes) > 1:
            merged_rows: list[dict] = []
            first_response: Dict[str, Any] | None = None

            for fc in codes:
                req2 = copy.deepcopy(request)
                ctx2 = req2.get("context") if isinstance(req2, dict) else None
                if not isinstance(ctx2, dict):
                    ctx2 = {}
                ctx2["factoryCode"] = fc
                ctx2.pop("factoryCodes", None)
                req2["context"] = ctx2

                resp = await self._execute_single(req2)
                if first_response is None and isinstance(resp, dict):
                    first_response = dict(resp)

                rows = resp.get("data") if isinstance(resp, dict) else None
                if isinstance(rows, list):
                    for r in rows:
                        if isinstance(r, dict) and "factoryCode" not in r:
                            r["factoryCode"] = fc
                        if isinstance(r, dict):
                            merged_rows.append(r)

            out = first_response or {"data": [], "count": 0}
            out["data"] = merged_rows
            out["count"] = len(merged_rows)
            return out

        # Single-factory / normal execution
        return await self._execute_single(request)

    async def _execute_single(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single-factory request through semantic->decision->data->response."""

        # 1. Semantic resolution
        semantic_plan = self._semantic_phase(request)

        # 2. Decision phase
        execution_plan = self._decision_phase(semantic_plan)

        # 2.5 KPI dynamic composition (config-driven)
        # If the user requests computed KPIs (ontology.metrics.*.formula), auto-build a computed plan
        # that fetches required base metrics and evaluates formulas. No per-KPI code required.
        execution_plan = self._maybe_build_dynamic_computed_plan(execution_plan)

        # 3. Data access phase
        data = await self._data_phase(execution_plan)

        # 4. Response (pass execution_plan so we can perform aggregations)
        response = self._response_phase(data, execution_plan)

        # If a factoryCode is provided via context, surface it as a column for UI grouping.
        try:
            ctx = request.get("context") if isinstance(request, dict) else None
            fc = ctx.get("factoryCode") if isinstance(ctx, dict) else None
            rows = response.get("data") if isinstance(response, dict) else None
            if fc and isinstance(rows, list):
                for r in rows:
                    if isinstance(r, dict) and "factoryCode" not in r:
                        r["factoryCode"] = str(fc)
        except Exception:
            pass

        try:
            rc = response.get("count") if isinstance(response, dict) else None
        except Exception:
            rc = None
        logger.info("Planner.done", extra={"row_count": rc})

        return response

    def _maybe_build_dynamic_computed_plan(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(execution_plan, dict):
            return execution_plan
        if str(execution_plan.get("type") or "").lower() == "computed":
            return execution_plan

        requested = execution_plan.get("metrics")
        if not isinstance(requested, list) or not requested:
            return execution_plan

        metrics_cfg = _load_ontology_metrics()
        if not metrics_cfg:
            return execution_plan

        base_metrics, computed_metrics = _resolve_metric_dependencies(requested, metrics_cfg)
        if not computed_metrics:
            return execution_plan

        # Build computed plan with one step per required base metric.
        steps = []
        for bm in base_metrics:
            mdef = metrics_cfg.get(bm) if isinstance(metrics_cfg, dict) else None
            entity = None
            if isinstance(mdef, dict):
                entity = mdef.get("entity")
            steps.append({"template_metric": bm, "entity": entity, "as": bm})

        # The response phase can infer variables mapping from depends_on if not supplied.
        formula_specs = [{"metric": cm} for cm in computed_metrics]

        auth = execution_plan.get("auth")
        if not isinstance(auth, dict) or not auth:
            auth = None

        out = {
            "type": "computed",
            "entity": execution_plan.get("entity"),
            "action": execution_plan.get("action"),
            "group_by": execution_plan.get("group_by") or ["date"],
            "filters": dict(execution_plan.get("filters") or {}),
            "metrics": requested,
            "base_metrics": base_metrics,
            "steps": steps,
            "formula": formula_specs,
            "viz": execution_plan.get("viz") or "table",
        }

        if auth:
            out["auth"] = auth

        return out

    # ------------------------------------------------------------------
    # Internal phases (kept explicit for debuggability)
    # ------------------------------------------------------------------

    def _semantic_phase(self, request: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("Planner.semantic.start")
        result = self.semantic_resolver.resolve(request)
        logger.debug("Planner.semantic.done", extra={"semantic_plan": self._redact_for_log(result)})
        return result

    def _decision_phase(self, semantic_plan: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("Planner.decision.start")
        result = self.decision_engine.decide(semantic_plan)
        logger.debug("Planner.decision.done", extra={"execution_plan": self._redact_for_log(result)})
        return result

    async def _data_phase(self, execution_plan: Dict[str, Any]):
        logger.debug("Planner.data.start")
        # Computed template: run steps and return named payloads
        if str(execution_plan.get("type") or "").lower() == "computed":
            steps = execution_plan.get("steps") or []
            if not isinstance(steps, list) or not steps:
                return {"__computed__": []}

            results: Dict[str, Any] = {}
            for step in steps:
                if not isinstance(step, dict):
                    continue
                tid = step.get("template_id")
                alias = step.get("as") or tid

                # Dynamic computed plan: step might specify a metric instead of a template_id.
                step_metric = step.get("template_metric")
                step_entity = step.get("entity")
                if not tid and step_metric:
                    # Force QueryBuilder selection by metric
                    subplan = {
                        "entity": (step_entity or execution_plan.get("entity")),
                        "action": execution_plan.get("action"),
                        "group_by": execution_plan.get("group_by"),
                        "filters": dict(execution_plan.get("filters") or {}),
                        "metrics": [str(step_metric)],
                    }
                    auth = execution_plan.get("auth")
                    if isinstance(auth, dict) and auth:
                        subplan["auth"] = auth
                    try:
                        from .query_builder import QueryBuilder

                        subplan = QueryBuilder().build(subplan)
                    except Exception:
                        pass
                    rows = await self.data_adapter.execute(subplan)
                    results[str(alias or step_metric)] = {"rows": rows, "plan": subplan}
                    continue

                if not tid:
                    continue

                # Subplan: same filters/group_by as parent, but force template_id
                subplan = {
                    "entity": execution_plan.get("entity"),
                    "action": execution_plan.get("action"),
                    "group_by": execution_plan.get("group_by"),
                    "filters": dict(execution_plan.get("filters") or {}),
                    "metrics": None,
                    "template_id": tid,
                }
                auth = execution_plan.get("auth")
                if isinstance(auth, dict) and auth:
                    subplan["auth"] = auth
                # Let QueryBuilder enrich method/endpoint/query mapping
                try:
                    from .query_builder import QueryBuilder

                    subplan = QueryBuilder().build(subplan)
                except Exception:
                    pass

                rows = await self.data_adapter.execute(subplan)
                results[str(alias)] = {"rows": rows, "plan": subplan}

            logger.debug("Planner.data.done", extra={"computed_steps": list(results.keys())})
            return results

        result = await self.data_adapter.execute(execution_plan)
        logger.debug("Planner.data.done", extra={"rows": len(result)})
        return result

    def _response_phase(self, data, execution_plan=None):
        logger.debug("Planner.response.start")
        # Computed response
        if execution_plan and str(execution_plan.get("type") or "").lower() == "computed":
            metrics_cfg = _load_ontology_metrics()
            formula_spec_raw = execution_plan.get("formula") or {}
            formula_specs = formula_spec_raw if isinstance(formula_spec_raw, list) else [formula_spec_raw]

            # Aggregate each step to a per-group series using template-driven measure + dimension_fields
            group_by = execution_plan.get("group_by")
            if isinstance(group_by, str):
                group_dims = [group_by.strip()] if group_by.strip() else ["date"]
            elif isinstance(group_by, list) and group_by:
                group_dims = [str(x).strip() for x in group_by if str(x).strip()] or ["date"]
            else:
                group_dims = ["date"]

            # Aggregate each step to a per-date series using template-driven measure + dimension_fields
            def _normalize_date_value(raw: Any) -> str:
                s = str(raw).strip() if raw is not None else ""
                if not s:
                    return ""

                # If already a date string, keep it.
                if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
                    if len(s) == 10:
                        return s

                # Convert ISO timestamps (often UTC 'Z') to local date if configured.
                if "T" in s:
                    try:
                        iso = s[:-1] + "+00:00" if s.endswith("Z") else s
                        dt = datetime.fromisoformat(iso)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)

                        off_raw = os.getenv("APP_TZ_OFFSET_HOURS") or os.getenv("LOCAL_TZ_OFFSET_HOURS") or "0"
                        offset_hours = int(str(off_raw).strip())
                        tz = timezone(timedelta(hours=offset_hours))
                        return dt.astimezone(tz).date().isoformat()
                    except Exception:
                        pass

                # Fallback: best-effort YYYY-MM-DD prefix
                return s[:10]

            def aggregate_step(step_payload: dict) -> Dict[tuple, float]:
                plan = (step_payload or {}).get("plan") or {}
                rows = (step_payload or {}).get("rows") or []
                if not isinstance(rows, list) or not rows:
                    return {}

                dim_fields = plan.get("dimension_fields") or {}
                if not isinstance(dim_fields, dict):
                    dim_fields = {}

                dim_defaults = plan.get("dimension_defaults") or {}
                if not isinstance(dim_defaults, dict):
                    dim_defaults = {}

                def _candidates_for_dim(dim: str) -> list[str]:
                    c = dim_fields.get(dim)
                    if isinstance(c, list) and c:
                        return [str(x) for x in c if str(x).strip()]
                    # sensible fallbacks
                    if dim == "date":
                        return ["date", "actualDate", "occurDate", "planDate", "createdAt"]
                    return [dim]

                measure = plan.get("measure") or {}
                if not isinstance(measure, dict):
                    measure = {}
                op = str(measure.get("op") or "sum").lower()
                field = measure.get("field")
                assume_one_if_missing = bool(measure.get("assume_one_if_missing") is True)

                def _extract_measure_value(row: dict) -> float | None:
                    """Extract numeric measure from a row using template-driven field(s)."""
                    if op == "count":
                        return 1.0

                    # If caller didn't provide a field for sum/avg/etc, treat each row as 1.
                    # This keeps computed KPIs usable even when the source API is a serial-level list.
                    if field is None:
                        return 1.0

                    # Support multiple candidate fields (first numeric wins)
                    if isinstance(field, (list, tuple)):
                        for f in field:
                            if f is None or (isinstance(f, str) and not f.strip()):
                                continue
                            v = _safe_get_path(row, str(f))
                            num = _safe_number(v)
                            if num is not None:
                                return float(num)
                        return 1.0 if assume_one_if_missing else None

                    v = _safe_get_path(row, str(field))
                    num = _safe_number(v)
                    if num is not None:
                        return float(num)
                    return 1.0 if assume_one_if_missing else None

                out: Dict[tuple, float] = {}
                for r in rows:
                    if not isinstance(r, dict):
                        continue

                    key_parts: list[str] = []
                    for dim in group_dims:
                        dim_val = None
                        for p in _candidates_for_dim(dim):
                            v = _safe_get_path(r, p)
                            if v is not None and str(v).strip() != "":
                                dim_val = str(v)
                                break
                        if dim_val is None:
                            default_val = dim_defaults.get(dim)
                            if default_val is not None and str(default_val).strip() != "":
                                dim_val = str(default_val)
                            else:
                                dim_val = ""
                        if dim == "date" and dim_val:
                            dim_val = _normalize_date_value(dim_val)
                        key_parts.append(dim_val)
                    # skip rows that don't have group keys
                    if any(x == "" for x in key_parts):
                        continue

                    key = tuple(key_parts)

                    if op == "count":
                        out[key] = float(out.get(key, 0.0) + 1.0)
                        continue

                    num = _extract_measure_value(r)
                    if num is None:
                        continue
                    out[key] = float(out.get(key, 0.0) + num)
                return out

            step_series: Dict[str, Dict[tuple, float]] = {}
            for alias, payload in (data or {}).items() if isinstance(data, dict) else []:
                if not isinstance(payload, dict):
                    continue
                step_series[str(alias)] = aggregate_step(payload)

            # Union all group keys across step series
            all_keys = set()
            for series in step_series.values():
                all_keys.update(series.keys())

            def _metric_missing_as_zero(metric_id: str) -> bool:
                mdef = metrics_cfg.get(metric_id) if isinstance(metrics_cfg, dict) else None
                return bool(isinstance(mdef, dict) and mdef.get("missing_as_zero") is True)

            def _metric_precision(metric_id: str) -> int | None:
                mdef = metrics_cfg.get(metric_id) if isinstance(metrics_cfg, dict) else None
                if not isinstance(mdef, dict):
                    return None
                p = mdef.get("precision")
                try:
                    return int(p) if p is not None else None
                except Exception:
                    return None

            rows_out = []
            for key in sorted(all_keys):
                # key -> group fields
                row = {}
                if len(group_dims) == 1:
                    row[group_dims[0]] = key[0]
                else:
                    for idx, dim in enumerate(group_dims):
                        row[dim] = key[idx]

                # base variables from steps
                base_vars: Dict[str, Any] = {}
                for alias, series in step_series.items():
                    base_vars[alias] = series.get(key)

                # Evaluate each requested formula
                for spec in formula_specs:
                    if not isinstance(spec, dict):
                        continue
                    metric_name = spec.get("metric")
                    if not metric_name or not isinstance(metric_name, str):
                        continue

                    metric_def = metrics_cfg.get(metric_name) if isinstance(metrics_cfg, dict) else None
                    formula = None
                    if isinstance(metric_def, dict):
                        formula = metric_def.get("formula")
                    if not formula:
                        formula = spec.get("formula")
                    if not isinstance(formula, str) or not formula.strip():
                        continue

                    # Variables mapping: prefer explicit template mapping; else infer from depends_on
                    var_map = spec.get("variables") if isinstance(spec.get("variables"), dict) else None
                    if not var_map and isinstance(metric_def, dict):
                        deps = metric_def.get("depends_on")
                        if isinstance(deps, list) and deps:
                            var_map = {str(d): str(d) for d in deps if str(d).strip()}

                    if not isinstance(var_map, dict) or not var_map:
                        continue

                    variables: Dict[str, Any] = {}
                    base_values: Dict[str, Any] = {}
                    missing_hard = False
                    for var_name, ref in var_map.items():
                        alias = str(ref).split(".", 1)[0] if isinstance(ref, str) else None
                        v = base_vars.get(alias) if alias else None
                        if v is None:
                            if _metric_missing_as_zero(str(var_name)):
                                v = 0.0
                            else:
                                missing_hard = True
                        variables[str(var_name)] = v
                        base_values[str(var_name)] = v

                    # Put base values into row (useful for debugging/trace)
                    row.update(base_values)

                    value = None if missing_hard else _safe_eval_formula(formula, variables)
                    prec = _metric_precision(metric_name)
                    if value is not None and prec is not None:
                        try:
                            value = round(float(value), prec)
                        except Exception:
                            pass
                    # UI-friendly display for undefined KPIs (e.g. division by zero)
                    if metric_name == "defect_ppm" and value is None:
                        row[metric_name] = "N/A"
                    else:
                        row[metric_name] = value

                rows_out.append(row)

            return {"data": rows_out, "count": len(rows_out)}
        # If caller requested grouping, perform simple aggregations here
        group_by = (execution_plan or {}).get("group_by") if execution_plan else None
        order_by = (execution_plan or {}).get("order_by") if execution_plan else None

        def _apply_order_by(rows, ob):
            if not isinstance(rows, list) or not rows:
                return rows
            if not isinstance(ob, dict):
                return rows
            field = ob.get("field")
            if not field or not isinstance(field, str):
                return rows
            direction = str(ob.get("direction") or "desc").lower()
            reverse = direction != "asc"

            def key_fn(r):
                if not isinstance(r, dict):
                    return float("-inf") if reverse else float("inf")
                v = r.get(field)
                if v is None:
                    return float("-inf") if reverse else float("inf")
                # numeric
                if isinstance(v, (int, float)):
                    return float(v)
                try:
                    return float(str(v).replace(",", ""))
                except Exception:
                    return str(v)

            try:
                rows.sort(key=key_fn, reverse=reverse)
            except Exception:
                # keep original order if sorting fails
                return rows
            return rows

        def _normalize_group_by(gb):
            if gb is None:
                return None
            if isinstance(gb, list):
                parts = [str(x).strip() for x in gb if str(x).strip()]
                return parts or None
            if isinstance(gb, str):
                s = gb.strip()
                if not s:
                    return None
                if "," in s:
                    parts = [p.strip() for p in s.split(",") if p.strip()]
                    return parts or None
                return s
            return None

        group_by = _normalize_group_by(group_by)

        # Keep backwards-compatible line-only aggregation
        if group_by == "line" or group_by == ["line"]:
            # Aggregate numeric metrics by line id/name
            agg = {}

            def _extract_line_ident(row: dict):
                line_obj = row.get("line") or {}
                pk = line_obj.get("pk") or {}
                line_id = pk.get("id") or line_obj.get("id") or row.get("lineId") or row.get("line_pk")
                line_name = line_obj.get("name") or row.get("lineName") or row.get("line_name")
                parent = line_obj.get("parentCode") if isinstance(line_obj, dict) else None
                if isinstance(parent, dict):
                    line_code = parent.get("code") or parent.get("value")
                else:
                    line_code = None
                line_code = line_code or line_obj.get("code") or pk.get("code") or row.get("lineCode") or row.get("line_code")
                key = str(line_code) if line_code is not None else (str(line_id) if line_id is not None else "__unknown__")
                return key, line_id, line_code, line_name

            def _extract_order_key(row: dict):
                # common flat keys
                for k in [
                    "productionOrderId",
                    "orderId",
                    "poId",
                    "poNo",
                    "orderNo",
                    "orderCode",
                    "poCode",
                ]:
                    v = row.get(k)
                    if v is not None and not isinstance(v, (dict, list)):
                        return v

                # common nested pk shapes
                for nested in ["pk", "productionOrder", "order"]:
                    obj = row.get(nested)
                    if isinstance(obj, dict):
                        pk = obj.get("pk") if isinstance(obj.get("pk"), dict) else None
                        if pk:
                            v = pk.get("id") or pk.get("code")
                            if v is not None and not isinstance(v, (dict, list)):
                                return v
                        v = obj.get("id") or obj.get("code")
                        if v is not None and not isinstance(v, (dict, list)):
                            return v

                return None

            for row in data:
                # try to find line id and name in common shapes
                key, line_id, line_code, line_name = _extract_line_ident(row)

                if key not in agg:
                    agg[key] = {
                        "__lineId": line_id,
                        "__lineKey": key,
                        "lineCode": line_code,
                        "lineName": line_name,
                        "orderCount": 0,
                        "totalPlanQty": 0.0,
                        "totalDefectQty": 0.0,
                        "sumTactTime": 0.0,
                        "totalActualQty": 0.0,
                        "prodStatusSet": set(),
                        "processTypeSet": set(),
                        "__seenOrders": set(),
                    }

                item = agg[key]

                order_key = _extract_order_key(row)
                if order_key is not None:
                    if order_key not in item["__seenOrders"]:
                        item["__seenOrders"].add(order_key)
                        item["orderCount"] += 1
                        try:
                            item["totalPlanQty"] += float(row.get("planQty") or 0)
                        except Exception:
                            pass
                        try:
                            item["totalDefectQty"] += float(row.get("defectQty") or 0)
                        except Exception:
                            pass
                        try:
                            item["totalActualQty"] += float(row.get("actualQty") or 0)
                        except Exception:
                            pass
                        try:
                            item["sumTactTime"] += float(row.get("tactTime") or 0)
                        except Exception:
                            pass
                else:
                    item["orderCount"] += 1
                    try:
                        item["totalPlanQty"] += float(row.get("planQty") or 0)
                    except Exception:
                        pass
                    try:
                        item["totalDefectQty"] += float(row.get("defectQty") or 0)
                    except Exception:
                        pass
                    try:
                        item["totalActualQty"] += float(row.get("actualQty") or 0)
                    except Exception:
                        pass
                    try:
                        item["sumTactTime"] += float(row.get("tactTime") or 0)
                    except Exception:
                        pass
                # collect distinct production status codes
                try:
                    ps = row.get("prodStatus") or {}
                    ps_code = ps.get("code") if isinstance(ps, dict) else None
                    if ps_code:
                        item["prodStatusSet"].add(ps_code)
                except Exception:
                    pass
                # collect distinct process type codes
                try:
                    proc = row.get("process") or {}
                    proc_code = proc.get("code") if isinstance(proc, dict) else None
                    if proc_code:
                        item["processTypeSet"].add(proc_code)
                except Exception:
                    pass
                # tactTime summed above (prefer de-duplicated per-order when possible)

            # finalize aggregates (compute averages)
            result = []

            def extract_label(obj, code):
                if not isinstance(obj, dict):
                    return code

                # Most common explicit localized keys (prefer vi/en)
                preferred_keys = [
                    "label_vi",
                    "labelVi",
                    "vi",
                    "label_en",
                    "labelEn",
                    "en",
                    "label",
                    "name",
                    "displayName",
                    "description",
                ]
                for key in preferred_keys:
                    v = obj.get(key)
                    if isinstance(v, str) and v.strip():
                        return v.strip()

                # Some APIs nest labels under a sub-object
                nested = obj.get("labels") or obj.get("label")
                if isinstance(nested, dict):
                    for key in ["vi", "en", "label_vi", "label_en"]:
                        v = nested.get(key)
                        if isinstance(v, str) and v.strip():
                            return v.strip()
                    for k, v in nested.items():
                        if isinstance(v, str) and v.strip():
                            return v.strip()

                # Fallback: any field that looks like a label/name
                for k, v in obj.items():
                    if not isinstance(v, str) or not v.strip():
                        continue
                    lk = str(k).lower()
                    if "label" in lk or lk.endswith("name") or lk == "name":
                        return v.strip()

                return code

            for k, v in agg.items():
                avg_tact = v["sumTactTime"] / v["orderCount"] if v["orderCount"] else None
                # Lấy label cho productionStatusCodes từ từng row trong data
                prod_status_labels = []
                process_type_labels = []
                # Tìm các row thuộc line này
                target_key = v.get("__lineKey")
                line_rows = [row for row in data if _extract_line_ident(row)[0] == target_key]
                # Lấy label cho từng code
                for code in sorted(list(v.get("prodStatusSet") or [])):
                    label = code
                    for row in line_rows:
                        ps = row.get("prodStatus")
                        if isinstance(ps, dict) and (ps.get("code") == code):
                            label = extract_label(ps, code)
                            break
                    prod_status_labels.append(label)
                for code in sorted(list(v.get("processTypeSet") or [])):
                    label = code
                    for row in line_rows:
                        proc = row.get("process")
                        if isinstance(proc, dict) and (proc.get("code") == code):
                            label = extract_label(proc, code)
                            break
                    process_type_labels.append(label)

                result.append({
                    "lineCode": v.get("lineCode"),
                    "lineName": v.get("lineName"),
                    "orderCount": v["orderCount"],
                    "totalPlanQty": v["totalPlanQty"],
                    "totalDefectQty": v["totalDefectQty"],
                    "totalActualQty": v.get("totalActualQty", 0.0),
                    "avgTactTime": avg_tact,
                    "productionStatusCount": len(v.get("prodStatusSet") or []),
                    "productionStatusCodes": sorted(list(v.get("prodStatusSet") or [])),
                    "productionStatusLabels": prod_status_labels,
                    "processTypeCount": len(v.get("processTypeSet") or []),
                    "processTypes": sorted(list(v.get("processTypeSet") or [])),
                    "processTypeLabels": process_type_labels,
                })

            result = _apply_order_by(result, order_by)
            return {"data": result, "count": len(result)}

        # Generic multi-dimension aggregation (config-driven group_by list)
        if isinstance(group_by, list) and len(group_by) > 0:
            from datetime import datetime

            def primitive_key(value):
                """Return a hashable, stable key for grouping.

                MES payloads sometimes embed ids/pks as dicts; never allow dict/list as a key part.
                """
                if value is None:
                    return None
                if isinstance(value, (str, int, float, bool)):
                    return value
                if isinstance(value, dict):
                    # common id/code shapes
                    for k in ["code", "id", "value", "name"]:
                        v = value.get(k)
                        if v is not None and not isinstance(v, (dict, list)):
                            return v
                    pk = value.get("pk")
                    if isinstance(pk, dict):
                        return primitive_key(pk.get("id") or pk.get("code") or pk.get("value"))
                    # fallback to a stable string
                    try:
                        import json

                        return json.dumps(value, sort_keys=True, ensure_ascii=False)
                    except Exception:
                        return str(value)
                if isinstance(value, list):
                    return tuple(primitive_key(v) for v in value)
                return str(value)

            def extract_label(obj, code):
                if not isinstance(obj, dict):
                    return code

                preferred_keys = [
                    "label_vi",
                    "labelVi",
                    "vi",
                    "label_en",
                    "labelEn",
                    "en",
                    "label",
                    "name",
                    "displayName",
                    "description",
                ]
                for key in preferred_keys:
                    v = obj.get(key)
                    if isinstance(v, str) and v.strip():
                        return v.strip()

                nested = obj.get("labels") or obj.get("label")
                if isinstance(nested, dict):
                    for key in ["vi", "en", "label_vi", "label_en"]:
                        v = nested.get(key)
                        if isinstance(v, str) and v.strip():
                            return v.strip()
                    for _, v in nested.items():
                        if isinstance(v, str) and v.strip():
                            return v.strip()

                for k, v in obj.items():
                    if not isinstance(v, str) or not v.strip():
                        continue
                    lk = str(k).lower()
                    if "label" in lk or lk.endswith("name") or lk == "name":
                        return v.strip()
                return code

            def extract_line(row):
                line_obj = row.get("line") or {}
                pk = line_obj.get("pk") or {}
                line_id = pk.get("id") or line_obj.get("id") or row.get("lineId") or row.get("line_pk")
                line_name = line_obj.get("name") or row.get("lineName") or row.get("line_name")
                parent = line_obj.get("parentCode") if isinstance(line_obj, dict) else None
                if isinstance(parent, dict):
                    line_code = parent.get("code") or parent.get("value")
                else:
                    line_code = None
                line_code = line_code or line_obj.get("code") or pk.get("code") or row.get("lineCode") or row.get("line_code")
                # Prefer code for grouping; fallback to id
                return primitive_key(line_code) or primitive_key(line_id), line_name, line_code

            def extract_prod_status(row):
                ps = row.get("prodStatus")
                if isinstance(ps, dict):
                    code = ps.get("code")
                    if code:
                        return code, extract_label(ps, code)
                return None, None

            def extract_model(row):
                # MES payload commonly uses modelId as an object (not a scalar id)
                model_obj = row.get("modelId") or row.get("model")
                if isinstance(model_obj, dict):
                    # Prefer parentCode.code/name (real model code/name)
                    parent = model_obj.get("parentCode")
                    if isinstance(parent, dict):
                        code = parent.get("code")
                        name = parent.get("name") or parent.get("description")
                        if code or name:
                            return primitive_key(code), name if isinstance(name, str) and name.strip() else None

                    # fallback direct code/name
                    code = model_obj.get("code") or model_obj.get("modelCode")
                    name = (
                        model_obj.get("name")
                        or model_obj.get("modelName")
                        or model_obj.get("displayName")
                        or model_obj.get("description")
                    )
                    if code or name:
                        return primitive_key(code), name if isinstance(name, str) and name.strip() else None

                    # last-resort: try to stringify a stable id
                    return primitive_key(model_obj.get("pk") or model_obj.get("id") or model_obj), None

                # fallback flat keys
                code = primitive_key(row.get("modelCode") or row.get("modelPk") or row.get("model_id") or row.get("model"))
                name = row.get("modelName")
                return code, name if isinstance(name, str) and name.strip() else None

            def extract_process_type(row):
                proc = row.get("process")
                if isinstance(proc, dict):
                    code = proc.get("code")
                    label = proc.get("name") or proc.get("displayName") or proc.get("description")
                    if code:
                        return primitive_key(code), extract_label(proc, code)
                    if label and isinstance(label, str) and label.strip():
                        return primitive_key(label), label.strip()
                return None, None

            def extract_date(row):
                # Use the same candidates as month, but keep YYYY-MM-DD
                candidates = [
                    "planDate",
                    "plan_date",
                    "planStartDate",
                    "planStartTime",
                    "planStart",
                    "plannedDate",
                    "date",
                ]
                val = None
                for k in candidates:
                    if row.get(k):
                        val = row.get(k)
                        break
                if val is None and isinstance(row.get("plan"), dict):
                    for k in candidates:
                        if row["plan"].get(k):
                            val = row["plan"].get(k)
                            break
                if not val:
                    return None
                s = str(val)
                try:
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                except Exception:
                    try:
                        dt = datetime.fromisoformat(s.split("T")[0])
                    except Exception:
                        # if already YYYY-MM-DD
                        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
                            return s[:10]
                        return None
                return dt.date().isoformat()

            def extract_year(row):
                d = extract_date(row)
                if not d:
                    return None
                # d is YYYY-MM-DD
                try:
                    return int(str(d)[:4])
                except Exception:
                    return None

            def extract_quarter(row):
                d = extract_date(row)
                if not d:
                    return None
                try:
                    y = int(str(d)[:4])
                    m = int(str(d)[5:7])
                    q = (m - 1) // 3 + 1
                    return f"{y:04d}-Q{q}"
                except Exception:
                    return None

            def extract_week(row):
                # ISO week number: YYYY-Www
                d = extract_date(row)
                if not d:
                    return None
                try:
                    dt = datetime.fromisoformat(str(d))
                    iso_year, iso_week, _ = dt.isocalendar()
                    return f"{iso_year:04d}-W{iso_week:02d}"
                except Exception:
                    return None

            def extract_month(row):
                # Try common fields
                candidates = [
                    "planDate",
                    "plan_date",
                    "planStartDate",
                    "planStartTime",
                    "planStart",
                    "plannedDate",
                    "date",
                ]
                val = None
                for k in candidates:
                    if row.get(k):
                        val = row.get(k)
                        break
                if val is None and isinstance(row.get("plan"), dict):
                    for k in candidates:
                        if row["plan"].get(k):
                            val = row["plan"].get(k)
                            break
                if not val:
                    return None
                s = str(val)
                # Accept ISO date/time
                try:
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                except Exception:
                    try:
                        dt = datetime.fromisoformat(s.split("T")[0])
                    except Exception:
                        return None
                return f"{dt.year:04d}-{dt.month:02d}"

            agg = {}
            for row in data:
                key_parts = []
                group_fields: Dict[str, Any] = {}

                for dim in group_by:
                    d = str(dim)
                    if d == "line":
                        line_key, line_name, line_code = extract_line(row)
                        key_parts.append(line_key)
                        group_fields["lineCode"] = line_code or line_key
                        group_fields["lineName"] = line_name
                    elif d == "month":
                        m = extract_month(row)
                        key_parts.append(m)
                        group_fields["month"] = m
                    elif d == "year":
                        y = extract_year(row)
                        key_parts.append(y)
                        group_fields["year"] = y
                    elif d == "quarter":
                        q = extract_quarter(row)
                        key_parts.append(q)
                        group_fields["quarter"] = q
                    elif d == "week":
                        w = extract_week(row)
                        key_parts.append(w)
                        group_fields["week"] = w
                    elif d == "date":
                        dval = extract_date(row)
                        key_parts.append(dval)
                        group_fields["date"] = dval
                    elif d == "prodStatus":
                        code, label = extract_prod_status(row)
                        key_parts.append(code)
                        group_fields["productionStatusCode"] = code
                        group_fields["productionStatusLabel"] = label
                    elif d == "model":
                        model_code, model_name = extract_model(row)
                        key_parts.append(model_code or model_name)
                        group_fields["modelCode"] = model_code
                        group_fields["modelName"] = model_name
                    elif d == "processType":
                        pcode, plabel = extract_process_type(row)
                        key_parts.append(pcode)
                        group_fields["processTypeCode"] = pcode
                        group_fields["processTypeLabel"] = plabel
                    else:
                        # Unknown dimension -> ignore to stay resilient
                        continue

                key = tuple(key_parts)
                if key not in agg:
                    agg[key] = {
                        **group_fields,
                        "__orderCount": 0,
                        "totalPlanQty": 0.0,
                        "totalActualQty": 0.0,
                        "totalDefectQty": 0.0,
                        "sumTactTime": 0.0,
                    }

                item = agg[key]
                item["__orderCount"] += 1
                try:
                    item["totalPlanQty"] += float(row.get("planQty") or 0)
                except Exception:
                    pass
                try:
                    item["totalActualQty"] += float(row.get("actualQty") or 0)
                except Exception:
                    pass
                try:
                    item["totalDefectQty"] += float(row.get("defectQty") or 0)
                except Exception:
                    pass
                try:
                    item["sumTactTime"] += float(row.get("tactTime") or 0)
                except Exception:
                    pass

            result = []
            for _, v in agg.items():
                cnt = v.get("__orderCount") or 0
                avg_tact = v["sumTactTime"] / cnt if cnt else None
                v.pop("sumTactTime", None)
                v.pop("__orderCount", None)
                v["avgTactTime"] = avg_tact
                result.append(v)

            result = _apply_order_by(result, order_by)
            return {"data": result, "count": len(result)}

        # default: return raw rows
        return {"data": data, "count": len(data)}
