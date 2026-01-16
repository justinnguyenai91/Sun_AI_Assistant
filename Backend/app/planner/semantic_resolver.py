import re
from typing import Dict, Any

from .domain_registry import get_registry


class SemanticResolver:
    """
    Normalize intent into a semantic plan.
    Expects request to include 'intent' (dict from LLMIntentParser) and 'user_input'.
    """

    def resolve(self, request: Dict[str, Any]) -> Dict[str, Any]:
        intent = request.get("intent") or {}
        raw = intent.get("raw_query") or request.get("user_input") or ""

        registry = get_registry()

        params: Dict[str, Any] = {}
        auth: Dict[str, Any] = {}

        # ------------------------------------------------------------
        # KPI/metric selection (config-driven)
        # We only select metric IDs here; formulas and dependencies are defined in ontology.yaml.
        # ------------------------------------------------------------
        # Normalize common shorthand so ontology synonyms can stay clean.
        # Example: "defect %" -> "defect percent"
        metric_text = str(raw).replace("%", " percent ")
        metrics = registry.parse_metrics(metric_text)
        if metrics:
            params["metrics"] = metrics

        # ------------------------------------------------------------
        # Factory context (routing): prefer explicit request.context.factoryCode
        # ------------------------------------------------------------
        ctx = request.get("context") or {}
        if isinstance(ctx, dict):
            fc = ctx.get("factoryCode") or ctx.get("factory")
            if isinstance(fc, str) and fc.strip():
                params["factoryCode"] = fc.strip()

            # Pass-through a small set of optional adapter filters from context.
            # This is intentionally config/ops oriented (auth, routing, scoping).
            passthrough_keys = [
                "featureCode",
                "feature_code",
                "state",
                "factoryPks",
                "plantPks",
                "teamPks",
                "groupPks",
                "partPks",
                "linePks",
                "processPks",
                "finalYn",
                "reflect",
                "from",
                "to",
            ]
            for k in passthrough_keys:
                if k in ctx and ctx.get(k) is not None:
                    # do not override values extracted from text
                    params.setdefault(k, ctx.get(k))

            # Per-request MES token support (service mode).
            # Keep this out of params/filters to avoid leaking to logs or query params.
            token = (
                ctx.get("mesToken")
                or ctx.get("mes_token")
                or ctx.get("externalApiToken")
                or ctx.get("external_api_token")
                or ctx.get("externalApiBearer")
            )
            if isinstance(token, str) and token.strip():
                auth["mes_token"] = token.strip()

        # Allow inline mention in text (e.g., "FAC01", "DJVN1")
        if "factoryCode" not in params:
            m_fc = re.search(r"\b([A-Z]{2,6}\d{1,4})\b", str(raw).upper())
            if m_fc:
                params["factoryCode"] = m_fc.group(1)

        # ------------------------------------------------------------
        # Time range extraction (supports explicit VN month range)
        # Example: "từ tháng 3 đến tháng 9 năm 2025"
        # ------------------------------------------------------------
        time_range = None

        # ISO date range: from YYYY-MM-DD to YYYY-MM-DD
        m_iso = re.search(r"từ\s*(\d{4}-\d{2}-\d{2})\s*đến\s*(\d{4}-\d{2}-\d{2})", raw, re.IGNORECASE)
        if m_iso:
            time_range = {"from": m_iso.group(1), "to": m_iso.group(2)}

        # VN month range: từ tháng M đến tháng N năm YYYY
        if time_range is None:
            m_vn = re.search(r"từ\s*tháng\s*(\d{1,2})\s*đến\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", raw, re.IGNORECASE)
            if m_vn:
                from_m = int(m_vn.group(1))
                to_m = int(m_vn.group(2))
                year = int(m_vn.group(3))
                from_m = max(1, min(12, from_m))
                to_m = max(1, min(12, to_m))
                if to_m < from_m:
                    from_m, to_m = to_m, from_m

                # build YYYY-MM-01 .. YYYY-MM-lastDay
                from_date = f"{year:04d}-{from_m:02d}-01"
                # compute last day of month
                import calendar

                last_day = calendar.monthrange(year, to_m)[1]
                to_date = f"{year:04d}-{to_m:02d}-{last_day:02d}"
                time_range = {"from": from_date, "to": to_date}

        # ISO month range: from YYYY-MM to YYYY-MM (en/vi)
        if time_range is None:
            m_iso_month = re.search(r"\b(from|từ)\s*(\d{4})-(\d{2})\s*(to|đến)\s*(\d{4})-(\d{2})\b", raw, re.IGNORECASE)
            if m_iso_month:
                y1, m1 = int(m_iso_month.group(2)), int(m_iso_month.group(3))
                y2, m2 = int(m_iso_month.group(5)), int(m_iso_month.group(6))
                m1 = max(1, min(12, m1))
                m2 = max(1, min(12, m2))
                if (y2, m2) < (y1, m1):
                    y1, m1, y2, m2 = y2, m2, y1, m1
                import calendar

                from_date = f"{y1:04d}-{m1:02d}-01"
                last_day = calendar.monthrange(y2, m2)[1]
                to_date = f"{y2:04d}-{m2:02d}-{last_day:02d}"
                time_range = {"from": from_date, "to": to_date}

        # Single VN month marker: tháng MM/YYYY
        if time_range is None:
            m_one = re.search(r"tháng\s*(\d{1,2})\s*/\s*(\d{4})", raw, re.IGNORECASE)
            if m_one:
                mm = max(1, min(12, int(m_one.group(1))))
                yy = int(m_one.group(2))
                import calendar

                from_date = f"{yy:04d}-{mm:02d}-01"
                last_day = calendar.monthrange(yy, mm)[1]
                to_date = f"{yy:04d}-{mm:02d}-{last_day:02d}"
                time_range = {"from": from_date, "to": to_date}

        # Fallback: simple relative ranges ("6 tháng", "1 year", "3개월")
        if time_range is None:
            m = re.search(r"(\d+)\s*(năm|nam|year|years|년)", raw)
            if m:
                years = int(m.group(1))
                time_range = {"value": years, "unit": "years"}
            else:
                m2 = re.search(r"(\d+)\s*(tháng|thang|month|months|개월)", raw)
                if m2:
                    months = int(m2.group(1))
                    time_range = {"value": months, "unit": "months"}

        if time_range:
            params["time_range"] = time_range

        # Group-by extraction from text via registry (config-driven)
        group_by = registry.parse_group_by(raw)
        if group_by:
            params["group_by"] = group_by

        # ------------------------------------------------------------
        # Planning filters extraction (minimal)
        # Example:
        # - "poType NORMAL"
        # - "PO type: REWORK"
        # - "loại lệnh = NORMAL"
        # ------------------------------------------------------------
        m_potype = re.search(
            r"\b(?:po\s*type|potype|loại\s*lệnh|loai\s*lenh)\b\s*(?:[:=]|là|la|is)?\s*([A-Za-z0-9_\-]+)",
            raw,
            re.IGNORECASE,
        )
        if m_potype:
            params["poType"] = m_potype.group(1)

        # ------------------------------------------------------------
        # Order-by extraction (minimal, metric-focused)
        # Examples:
        # - "order by actual desc"
        # - "sort by defect"
        # - "xếp theo thực tế giảm dần"
        # ------------------------------------------------------------
        raw_lc = str(raw).lower()

        def _map_sort_field(text: str):
            if re.search(r"\b(line\s*code|linecode|mã\s*dây\s*chuyền|ma\s*day\s*chuyen)\b", text, re.IGNORECASE):
                return "lineCode"
            if re.search(r"\b(line\s*name|tên\s*dây\s*chuyền|ten\s*day\s*chuyen)\b", text, re.IGNORECASE):
                return "lineName"
            if re.search(r"\b(model\s*code|modelcode|mã\s*model|ma\s*model)\b", text, re.IGNORECASE):
                return "modelCode"
            if re.search(r"\b(model\s*name|tên\s*model|ten\s*model)\b", text, re.IGNORECASE):
                return "modelName"
            if re.search(r"\b(plan\s*date|planned\s*date|by\s*date|date|ngày|ngay)\b", text, re.IGNORECASE):
                return "date"
            if re.search(r"\b(month|tháng|thang)\b", text, re.IGNORECASE):
                return "month"
            if re.search(r"\b(week|weekly|tuần|tuan)\b", text, re.IGNORECASE):
                return "week"
            if re.search(r"\b(quarter|quarterly|quý|quy)\b", text, re.IGNORECASE):
                return "quarter"
            if re.search(r"\b(year|yearly|năm|nam)\b", text, re.IGNORECASE):
                return "year"
            if re.search(r"\b(status|trạng\s*thái|trang\s*thai)\b", text, re.IGNORECASE):
                return "productionStatusLabel"
            if re.search(r"\b(process\s*type|process|công\s*đoạn|cong\s*doan)\b", text, re.IGNORECASE):
                return "processTypeCode"
            if re.search(r"\b(actual|thực\s*tế|thuc\s*te)\b", text, re.IGNORECASE):
                return "totalActualQty"
            if re.search(r"\b(plan|planned|kế\s*hoạch|ke\s*hoach)\b", text, re.IGNORECASE):
                return "totalPlanQty"
            if re.search(r"\b(defect|lỗi|loi)\b", text, re.IGNORECASE):
                return "totalDefectQty"
            if re.search(r"\b(tact|takt)\b", text, re.IGNORECASE):
                return "avgTactTime"
            return None

        def _map_sort_dir(text: str):
            if re.search(r"\b(asc|ascending|tăng\s*dần|tang\s*dan)\b", text, re.IGNORECASE):
                return "asc"
            if re.search(r"\b(desc|descending|giảm\s*dần|giam\s*dan)\b", text, re.IGNORECASE):
                return "desc"
            return None

        sort_field = None
        sort_dir = None

        m_en = re.search(r"\b(order\s*by|sort\s*by)\s+([^\n\r]+)$", raw_lc, re.IGNORECASE)
        if m_en:
            clause = m_en.group(2)
            sort_field = _map_sort_field(clause)
            sort_dir = _map_sort_dir(clause)

        if sort_field is None:
            m_vi = re.search(r"\b(xếp\s*theo|sap\s*xep\s*theo|sắp\s*xếp\s*theo)\s+([^\n\r]+)$", raw_lc, re.IGNORECASE)
            if m_vi:
                clause = m_vi.group(2)
                sort_field = _map_sort_field(clause)
                sort_dir = _map_sort_dir(clause)

        if sort_field:
            params["order_by"] = {"field": sort_field, "direction": sort_dir or "desc"}

        out = {
            "intent": intent.get("intent"),
            "entity": intent.get("entity"),
            "raw_query": raw,
            "params": params,
        }
        if auth:
            out["auth"] = auth
        return out
