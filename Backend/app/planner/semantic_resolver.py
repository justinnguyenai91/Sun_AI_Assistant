import re
from typing import Dict, Any
from datetime import date

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
        # If not found in text and not set via context.factoryCode, try saved context
        if "factoryCode" not in params:
            m_fc = re.search(r"\b([A-Z]{2,6}\d{1,4})\b", str(raw).upper())
            if m_fc:
                params["factoryCode"] = m_fc.group(1)
            else:
                # Fallback to saved context from previous queries
                saved_context = request.get("_saved_context") if isinstance(request, dict) else None
                if isinstance(saved_context, dict):
                    saved_fc = saved_context.get("factory_code")
                    if saved_fc:
                        params["factoryCode"] = saved_fc
                        import logging
                        logging.getLogger(__name__).info(f"Using factoryCode from saved context: {saved_fc}")

        # ------------------------------------------------------------
        # Infer entity from saved context if not explicitly mentioned
        # This helps with follow-up queries like "thế còn tháng 11" or "từ tháng 9 đến 1"
        # ------------------------------------------------------------
        if "_saved_context" in request and isinstance(request.get("_saved_context"), dict):
            saved_context = request["_saved_context"]
            # If no entity mentioned and we have saved entity, use it
            if not intent.get("entity") or str(intent.get("entity", "")).strip() in ("", "None"):
                saved_entity = saved_context.get("last_entity")
                if saved_entity:
                    intent["entity"] = saved_entity
                    import logging
                    logging.getLogger(__name__).info(f"Using entity from saved context: {saved_entity}")

        # ------------------------------------------------------------
        # Time range extraction (supports explicit VN month range)
        # Example: "từ tháng 3 đến tháng 9 năm 2025"
        # ------------------------------------------------------------
        time_range = None
        time_granularity_hint: str | None = None

        def _safe_last_day_of_month(y: int, m: int) -> int:
            import calendar

            return calendar.monthrange(y, m)[1]

        def _quarter_to_dates(y: int, q: int) -> Dict[str, str] | None:
            try:
                q = int(q)
                if q < 1 or q > 4:
                    return None
                start_m = (q - 1) * 3 + 1
                end_m = start_m + 2
                from_date = f"{y:04d}-{start_m:02d}-01"
                to_date = f"{y:04d}-{end_m:02d}-{_safe_last_day_of_month(y, end_m):02d}"
                return {"from": from_date, "to": to_date}
            except Exception:
                return None

        def _iso_week_range(y1: int, w1: int, y2: int, w2: int) -> Dict[str, str] | None:
            try:
                from_d = date.fromisocalendar(int(y1), int(w1), 1)
                to_d = date.fromisocalendar(int(y2), int(w2), 7)
                if to_d < from_d:
                    from_d, to_d = to_d, from_d
                return {"from": from_d.isoformat(), "to": to_d.isoformat()}
            except Exception:
                return None

        # ============================================================
        # NOW - Current moment (treated as "today" for date filters)
        # ============================================================
        m_now = re.search(r"\b(hiện\s*tại|hien\s*tai|bây\s*giờ|bay\s*gio|lúc\s*này|luc\s*nay|now|right\s*now)\b", raw, re.IGNORECASE)
        if m_now:
            today = date.today()
            time_range = {"from": today.isoformat(), "to": today.isoformat()}

        # ============================================================
        # CURRENT_PERIOD - Today, this week, this month, this quarter, this year
        # ============================================================
        if time_range is None:
            # Hôm nay / today
            m_today = re.search(r"\b(hôm\s*nay|hom\s*nay|today)\b", raw, re.IGNORECASE)
            if m_today:
                today = date.today()
                time_range = {"from": today.isoformat(), "to": today.isoformat()}
        
        if time_range is None:
            # Tuần này / this week
            m_this_week = re.search(r"\b(tuần\s*này|tuan\s*nay|this\s*week)\b", raw, re.IGNORECASE)
            if m_this_week:
                today = date.today()
                iso_year, iso_week, iso_day = today.isocalendar()
                from_d = date.fromisocalendar(iso_year, iso_week, 1)
                to_d = date.fromisocalendar(iso_year, iso_week, 7)
                time_range = {"from": from_d.isoformat(), "to": to_d.isoformat()}
        
        if time_range is None:
            # Tháng này / this month
            m_this_month = re.search(r"\b(tháng\s*này|thang\s*nay|this\s*month)\b", raw, re.IGNORECASE)
            if m_this_month:
                today = date.today()
                from_date = f"{today.year:04d}-{today.month:02d}-01"
                last_day = _safe_last_day_of_month(today.year, today.month)
                to_date = f"{today.year:04d}-{today.month:02d}-{last_day:02d}"
                time_range = {"from": from_date, "to": to_date}
                time_granularity_hint = "month"
        
        if time_range is None:
            # Quý này / this quarter
            m_this_quarter = re.search(r"\b(quý\s*này|quy\s*nay|this\s*quarter)\b", raw, re.IGNORECASE)
            if m_this_quarter:
                today = date.today()
                current_quarter = (today.month - 1) // 3 + 1
                tr = _quarter_to_dates(today.year, current_quarter)
                if tr:
                    time_range = tr
        
        if time_range is None:
            # Năm nay / this year
            m_this_year = re.search(r"\b(năm\s*nay|nam\s*nay|this\s*year)\b", raw, re.IGNORECASE)
            if m_this_year:
                today = date.today()
                time_range = {"from": f"{today.year:04d}-01-01", "to": f"{today.year:04d}-12-31"}
                time_granularity_hint = "year"

        # ============================================================
        # PREVIOUS_PERIOD - Yesterday, last week, last month, last quarter, last year
        # ============================================================
        if time_range is None:
            # Hôm qua / yesterday
            m_yesterday = re.search(r"\b(hôm\s*qua|hom\s*qua|yesterday)\b", raw, re.IGNORECASE)
            if m_yesterday:
                from datetime import timedelta
                yesterday = date.today() - timedelta(days=1)
                time_range = {"from": yesterday.isoformat(), "to": yesterday.isoformat()}
        
        if time_range is None:
            # Tuần trước / last week
            m_last_week = re.search(r"\b(tuần\s*trước|tuan\s*truoc|last\s*week)\b", raw, re.IGNORECASE)
            if m_last_week:
                today = date.today()
                iso_year, iso_week, iso_day = today.isocalendar()
                # Go back 1 week
                if iso_week == 1:
                    iso_year -= 1
                    iso_week = 52  # Approximate
                else:
                    iso_week -= 1
                from_d = date.fromisocalendar(iso_year, iso_week, 1)
                to_d = date.fromisocalendar(iso_year, iso_week, 7)
                time_range = {"from": from_d.isoformat(), "to": to_d.isoformat()}
        
        if time_range is None:
            # Tháng trước / last month
            m_last_month = re.search(r"\b(tháng\s*trước|thang\s*truoc|last\s*month)\b", raw, re.IGNORECASE)
            if m_last_month:
                today = date.today()
                if today.month == 1:
                    last_month_year = today.year - 1
                    last_month = 12
                else:
                    last_month_year = today.year
                    last_month = today.month - 1
                from_date = f"{last_month_year:04d}-{last_month:02d}-01"
                last_day = _safe_last_day_of_month(last_month_year, last_month)
                to_date = f"{last_month_year:04d}-{last_month:02d}-{last_day:02d}"
                time_range = {"from": from_date, "to": to_date}
                time_granularity_hint = "month"
        
        if time_range is None:
            # Quý trước / last quarter
            m_last_quarter = re.search(r"\b(quý\s*trước|quy\s*truoc|last\s*quarter)\b", raw, re.IGNORECASE)
            if m_last_quarter:
                today = date.today()
                current_quarter = (today.month - 1) // 3 + 1
                if current_quarter == 1:
                    last_quarter_year = today.year - 1
                    last_quarter = 4
                else:
                    last_quarter_year = today.year
                    last_quarter = current_quarter - 1
                tr = _quarter_to_dates(last_quarter_year, last_quarter)
                if tr:
                    time_range = tr
        
        if time_range is None:
            # Năm trước / last year
            m_last_year = re.search(r"\b(năm\s*trước|nam\s*truoc|last\s*year)\b", raw, re.IGNORECASE)
            if m_last_year:
                today = date.today()
                last_year = today.year - 1
                time_range = {"from": f"{last_year:04d}-01-01", "to": f"{last_year:04d}-12-31"}
                time_granularity_hint = "year"

        # ============================================================
        # TO_DATE - Month/Quarter/Year to date (MTD, QTD, YTD)
        # ============================================================
        if time_range is None:
            # Month to date / MTD / từ đầu tháng đến nay
            m_mtd = re.search(r"\b(MTD|month[\s\-]*to[\s\-]*date|từ\s*đầu\s*tháng|tu\s*dau\s*thang)\b", raw, re.IGNORECASE)
            if m_mtd:
                today = date.today()
                from_date = f"{today.year:04d}-{today.month:02d}-01"
                time_range = {"from": from_date, "to": today.isoformat()}
                time_granularity_hint = "month"
        
        if time_range is None:
            # Quarter to date / QTD / từ đầu quý đến nay
            m_qtd = re.search(r"\b(QTD|quarter[\s\-]*to[\s\-]*date|từ\s*đầu\s*quý|tu\s*dau\s*quy)\b", raw, re.IGNORECASE)
            if m_qtd:
                today = date.today()
                current_quarter = (today.month - 1) // 3 + 1
                start_m = (current_quarter - 1) * 3 + 1
                from_date = f"{today.year:04d}-{start_m:02d}-01"
                time_range = {"from": from_date, "to": today.isoformat()}
        
        if time_range is None:
            # Year to date / YTD / từ đầu năm đến nay
            m_ytd = re.search(r"\b(YTD|year[\s\-]*to[\s\-]*date|từ\s*đầu\s*năm|tu\s*dau\s*nam)\b", raw, re.IGNORECASE)
            if m_ytd:
                today = date.today()
                from_date = f"{today.year:04d}-01-01"
                time_range = {"from": from_date, "to": today.isoformat()}
                time_granularity_hint = "year"

        # ISO date range: from YYYY-MM-DD to YYYY-MM-DD (supports VN + ASCII)
        m_iso = re.search(
            r"(từ|tu|from)\s*(\d{4}-\d{2}-\d{2})\s*(đến|den|to)\s*(\d{4}-\d{2}-\d{2})",
            raw,
            re.IGNORECASE,
        )
        if m_iso:
            time_range = {"from": m_iso.group(2), "to": m_iso.group(4)}

        # ISO week range: 2026-W01 ~ 2026-W06 (en/vi)
        if time_range is None:
            m_w = re.search(
                r"\b(\d{4})\s*-\s*W\s*(\d{1,2})\s*(?:~|\-|to|đến|den)\s*(\d{4})\s*-\s*W\s*(\d{1,2})\b",
                raw,
                re.IGNORECASE,
            )
            if m_w:
                y1, w1 = int(m_w.group(1)), int(m_w.group(2))
                y2, w2 = int(m_w.group(3)), int(m_w.group(4))
                tr = _iso_week_range(y1, w1, y2, w2)
                if tr:
                    time_range = tr

        # VN week range: "tuần 1 đến tuần 6 của năm 2026"
        if time_range is None:
            m_vn_week = re.search(
                r"tuần\s*(\d{1,2})\s*(?:đến|den)\s*tuần\s*(\d{1,2})\s*(?:của\s*)?(?:năm|nam)\s*(\d{4})",
                raw,
                re.IGNORECASE,
            )
            if m_vn_week:
                w1, w2, yy = int(m_vn_week.group(1)), int(m_vn_week.group(2)), int(m_vn_week.group(3))
                if w2 < w1:
                    w1, w2 = w2, w1
                tr = _iso_week_range(yy, w1, yy, w2)
                if tr:
                    time_range = tr

        # Quarter: Q1/2026, 2026-Q1, quý 1 năm 2026
        if time_range is None:
            m_q1 = re.search(r"\bQ\s*([1-4])\s*[/-]\s*(\d{4})\b", raw, re.IGNORECASE)
            m_q2 = re.search(r"\b(\d{4})\s*-\s*Q\s*([1-4])\b", raw, re.IGNORECASE)
            m_q3 = re.search(r"\bquý\s*([1-4])\s*(?:năm|nam)\s*(\d{4})\b", raw, re.IGNORECASE)
            q = y = None
            if m_q1:
                q, y = int(m_q1.group(1)), int(m_q1.group(2))
            elif m_q2:
                y, q = int(m_q2.group(1)), int(m_q2.group(2))
            elif m_q3:
                q, y = int(m_q3.group(1)), int(m_q3.group(2))
            if q and y:
                tr = _quarter_to_dates(y, q)
                if tr:
                    time_range = tr

        # Year: "năm 2025" / "year 2025"
        if time_range is None:
            m_y = re.search(r"\b(?:năm|nam|year)\s*(\d{4})\b", raw, re.IGNORECASE)
            if m_y:
                yy = int(m_y.group(1))
                time_range = {"from": f"{yy:04d}-01-01", "to": f"{yy:04d}-12-31"}
                time_granularity_hint = "year"

        # Year range: "từ năm YYYY đến năm YYYY"
        if time_range is None:
            m_yr = re.search(r"\b(từ|tu|from)\s*(?:năm|nam|year)\s*(\d{4})\s*(đến|den|to)\s*(?:năm|nam|year)?\s*(\d{4})\b", raw, re.IGNORECASE)
            if m_yr:
                y1 = int(m_yr.group(2))
                y2 = int(m_yr.group(4))
                if y2 < y1:
                    y1, y2 = y2, y1
                time_range = {"from": f"{y1:04d}-01-01", "to": f"{y2:04d}-12-31"}
                time_granularity_hint = "year"

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
                last_day = _safe_last_day_of_month(year, to_m)
                to_date = f"{year:04d}-{to_m:02d}-{last_day:02d}"
                time_range = {"from": from_date, "to": to_date}
                time_granularity_hint = "month"

        # VN month/year range (supports cross-year):
        # - "từ tháng 10/2025 đến 1/2026"
        # - "tu thang 10/2025 den thang 1/2026"
        # - "từ 10/2025 đến 01/2026"
        if time_range is None:
            m_my = re.search(
                r"(from|từ|tu)\s*(?:tháng|thang)?\s*(\d{1,2})\s*/\s*(\d{4})\s*(to|đến|den)\s*(?:tháng|thang)?\s*(\d{1,2})\s*/\s*(\d{4})",
                raw,
                re.IGNORECASE,
            )
            if m_my:
                m1, y1 = int(m_my.group(2)), int(m_my.group(3))
                m2, y2 = int(m_my.group(5)), int(m_my.group(6))
                m1 = max(1, min(12, m1))
                m2 = max(1, min(12, m2))
                if (y2, m2) < (y1, m1):
                    y1, m1, y2, m2 = y2, m2, y1, m1
                import calendar

                from_date = f"{y1:04d}-{m1:02d}-01"
                last_day = calendar.monthrange(y2, m2)[1]
                to_date = f"{y2:04d}-{m2:02d}-{last_day:02d}"
                time_range = {"from": from_date, "to": to_date}
                time_granularity_hint = "month"

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
                time_granularity_hint = "month"

        # English month name: "Jan 2026", "January 2026" (and other months)
        if time_range is None:
            month_map = {
                "jan": 1,
                "feb": 2,
                "mar": 3,
                "apr": 4,
                "may": 5,
                "jun": 6,
                "jul": 7,
                "aug": 8,
                "sep": 9,
                "oct": 10,
                "nov": 11,
                "dec": 12,
            }
            m_en_month = re.search(
                r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\s*(\d{4})\b",
                raw,
                re.IGNORECASE,
            )
            if m_en_month:
                key = m_en_month.group(1)[:3].lower()
                yy = int(m_en_month.group(2))
                mm = month_map.get(key)
                if mm:
                    import calendar

                    from_date = f"{yy:04d}-{mm:02d}-01"
                    last_day = calendar.monthrange(yy, mm)[1]
                    to_date = f"{yy:04d}-{mm:02d}-{last_day:02d}"
                    time_range = {"from": from_date, "to": to_date}
                    time_granularity_hint = "month"

        # Single VN month marker: tháng/thang MM/YYYY
        if time_range is None:
            m_one = re.search(r"(?:tháng|thang)\s*(\d{1,2})\s*/\s*(\d{4})", raw, re.IGNORECASE)
            if m_one:
                mm = max(1, min(12, int(m_one.group(1))))
                yy = int(m_one.group(2))
                import calendar

                from_date = f"{yy:04d}-{mm:02d}-01"
                last_day = calendar.monthrange(yy, mm)[1]
                to_date = f"{yy:04d}-{mm:02d}-{last_day:02d}"
                time_range = {"from": from_date, "to": to_date}
                time_granularity_hint = "month"

        # Fallback: simple relative ranges ("6 tháng", "1 year", "3개월")
        # Priority 1: "X tháng/tuần/năm gần nhất" (most recent)
        if time_range is None:
            # Match: "3 tháng gần nhất", "1 tuần gần nhất", "2 năm gần nhất"
            m_recent = re.search(
                r"(\d+)\s*(năm|nam|year|years|tháng|thang|month|months|tuần|tuan|week|weeks|ngày|ngay|day|days)\s*(?:gần\s*nhất|gan\s*nhat|recent|latest|last)",
                raw,
                re.IGNORECASE
            )
            if m_recent:
                value = int(m_recent.group(1))
                unit_text = m_recent.group(2).lower()
                # Normalize to standard units
                if any(x in unit_text for x in ["năm", "nam", "year"]):
                    time_range = {"value": value, "unit": "years"}
                elif any(x in unit_text for x in ["tháng", "thang", "month"]):
                    time_range = {"value": value, "unit": "months"}
                elif any(x in unit_text for x in ["tuần", "tuan", "week"]):
                    time_range = {"value": value, "unit": "weeks"}
                elif any(x in unit_text for x in ["ngày", "ngay", "day"]):
                    time_range = {"value": value, "unit": "days"}
        
        # Priority 2: Simple "X tháng", "X year" without "gần nhất"
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

        # ============================================================
        # BEFORE_AFTER - Before/after a specific date
        # ============================================================
        if time_range is None:
            # Before date: "trước ngày 2026-01-15" / "before 2026-01-15"
            m_before = re.search(r"\b(trước|truoc|before)\s*(?:ngày|ngay)?\s*(\d{4}-\d{2}-\d{2})\b", raw, re.IGNORECASE)
            if m_before:
                target_date = m_before.group(2)
                # Use a very early date as "from" (100 years ago)
                from datetime import timedelta
                early_date = (date.today() - timedelta(days=36500)).isoformat()
                time_range = {"from": early_date, "to": target_date}
        
        if time_range is None:
            # After date: "sau ngày 2026-01-15" / "after 2026-01-15"
            m_after = re.search(r"\b(sau|after)\s*(?:ngày|ngay)?\s*(\d{4}-\d{2}-\d{2})\b", raw, re.IGNORECASE)
            if m_after:
                target_date = m_after.group(2)
                # Use far future date as "to" (10 years ahead)
                from datetime import timedelta
                future_date = (date.today() + timedelta(days=3650)).isoformat()
                time_range = {"from": target_date, "to": future_date}

        # ============================================================
        # HOUR_RANGE - Hour range filter (stored for shift/time filter)
        # ============================================================
        # Pattern: "từ 8h đến 17h", "from 8:00 to 17:00"
        m_hour_range = re.search(r"\b(từ|tu|from)\s*(\d{1,2})(?:h|:|giờ)?\s*(?:00)?\s*(đến|den|to)\s*(\d{1,2})(?:h|:|giờ)?\s*(?:00)?\b", raw, re.IGNORECASE)
        if m_hour_range:
            hour_from = int(m_hour_range.group(2))
            hour_to = int(m_hour_range.group(4))
            if 0 <= hour_from <= 23 and 0 <= hour_to <= 23:
                params["hour_range"] = {"from": hour_from, "to": hour_to}

        if time_range:
            params["time_range"] = time_range

        # Group-by extraction from text via registry (config-driven)
        group_by = registry.parse_group_by(raw)

        # Detect defect symptom analysis patterns
        # This indicates user wants defect breakdown by symptom, not just total count
        # Patterns: "lỗi nào", "chi tiết lỗi", "hạng mục lỗi", "defect items", etc.
        # BUT: If user explicitly requests spatial dimensions (line, model, process), respect that instead
        if not group_by or not isinstance(group_by, list) or "symptom" not in group_by:
            # Check if user wants ANY dimension grouping (time or spatial)
            # Spatial: "theo line", "cho line", "theo từng line", "cho từng line", "by line", "by model"
            # Time: "theo tháng", "cho tháng", "by month", etc.
            spatial_dimension_pattern = r"\b((theo|cho)\s+(từng\s+|mỗi\s+|each\s+)?(line|dây|day|model|mẫu|mau|process|công\s*đoạn|cong\s*doan)|by\s+(each\s+)?(line|model|process))\b"
            time_dimension_pattern = r"\b((theo|cho)\s+(từng\s+|mỗi\s+|each\s+)?(tháng|thang|ngày|ngay|tuần|tuan|quý|quy|năm|nam|ca|shift)|by\s+(each\s+)?(month|day|week|quarter|year|shift))\b"
            
            has_spatial_grouping = re.search(spatial_dimension_pattern, raw, re.IGNORECASE)
            has_time_grouping = re.search(time_dimension_pattern, raw, re.IGNORECASE)
            
            # Defect symptom breakdown patterns
            defect_pattern = r"\b(" \
                r"lỗi\s+nào|loi\s+nao|" \
                r"lỗi\s+nhiều\s*nhất|loi\s+nhieu\s*nhat|" \
                r"loại\s+lỗi|loai\s+loi|" \
                r"dạng\s+lỗi|dang\s+loi|" \
                r"chi\s*tiết\s+lỗi|chi\s*tiet\s+loi|" \
                r"chi\s*tiết\s+defect|chi\s*tiet\s+defect|" \
                r"chi\s*tiết\s+(defect\s+)?symptom|chi\s*tiet\s+(defect\s+)?symptom|" \
                r"chi\s*tiết\s+hạng\s*mục\s+lỗi|chi\s*tiet\s+hang\s*muc\s+loi|" \
                r"hạng\s*mục\s+lỗi|hang\s*muc\s+loi|" \
                r"danh\s*sách\s+lỗi|danh\s*sach\s+loi|" \
                r"liệt\s*kê\s+lỗi|liet\s*ke\s+loi|" \
                r"phân\s*tích\s+lỗi|phan\s*tich\s+loi|" \
                r"defect\s+items?|" \
                r"defect\s+symptom\s+items?|" \
                r"defect\s+types?|" \
                r"error\s+types?|" \
                r"defect\s+breakdown|" \
                r"error\s+breakdown|" \
                r"symptom\s+breakdown|" \
                r"symptom\s+analysis|" \
                r"defect\s+details?|" \
                r"error\s+details?|" \
                r"list\s+of\s+(defects?|errors?)|" \
                r"which\s+(error|defect)|" \
                r"top.*lỗi|top.*loi" \
                r")\b"
            
            # Add symptom grouping ONLY if:
            # 1. Defect pattern detected (chi tiết lỗi, lỗi nào, etc.)
            # 2. No explicit spatial dimension requested (theo line, by model)
            # 3. No time dimension requested (theo tháng, by day)
            # Reasoning: "chi tiết lỗi theo line" → user wants line grouping with defect details, NOT symptom breakdown
            if re.search(defect_pattern, raw, re.IGNORECASE) and not has_spatial_grouping and not has_time_grouping:
                if not group_by:
                    group_by = ["symptom"]
                elif isinstance(group_by, list) and "symptom" not in group_by:
                    group_by.append("symptom")
                import logging
                logging.getLogger(__name__).info(f"Detected defect symptom pattern (no dimension conflict) → added group_by symptom")

        # If user asked for a specific month (e.g., "Jan 2026" / "tháng 1/2026")
        # but didn't specify a grouping dimension, default to monthly buckets.
        if (not group_by) and time_granularity_hint == "month":
            group_by = ["month"]

        # Clean up time-based grouping when symptom is primary dimension
        # Symptom queries should treat time as filter, not grouping
        # But keep spatial dimensions (line/model/process) if they exist
        if isinstance(group_by, list) and group_by and "symptom" in group_by:
            # Remove only time-based dimensions, keep spatial ones
            original_group_by = group_by.copy()
            group_by = [g for g in group_by if g not in ("date", "week", "month", "quarter", "year", "shift")]
            
            if not group_by:
                group_by = ["symptom"]
            import logging
            if original_group_by != group_by:
                logging.getLogger(__name__).info(f"Removed time dimensions from symptom query: {original_group_by} → {group_by}")

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

        # ------------------------------------------------------------
        # Top/Bottom N parsing (ranking-lite)
        # Examples:
        # - "Top 5 ..."
        # - "Worst 10 ..."
        # - "Top 5 loại lỗi" (Pareto)
        # This sets limit + a reasonable default order_by if user didn't specify one.
        # ------------------------------------------------------------
        limit = None
        m_top = re.search(r"\b(top|worst|bottom)\s*(\d{1,3})\b", raw_lc, re.IGNORECASE)
        if m_top:
            try:
                limit = int(m_top.group(2))
                if limit <= 0:
                    limit = None
            except Exception:
                limit = None
        if limit is None:
            m_top_vi = re.search(r"\b(top)\s*(\d{1,3})\b", raw_lc, re.IGNORECASE)
            if m_top_vi:
                try:
                    limit = int(m_top_vi.group(2))
                except Exception:
                    limit = None

        if isinstance(limit, int) and limit > 0:
            params["limit"] = limit

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
                # For quality surface outputs, the metric column is often defect_count.
                # For PO summary outputs, the metric column is totalDefectQty.
                if re.search(r"\b(defect\s*count|number\s*of\s*defects|số\s*lỗi|so\s*loi|ng)\b", text, re.IGNORECASE):
                    return "defect_count"
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

        # If user asked for Top N but didn't specify sorting, pick a sensible default.
        if isinstance(limit, int) and limit > 0 and "order_by" not in params:
            # If the query is about defects/symptoms, default to defect_count desc.
            if re.search(r"\b(defect|lỗi|loi|ppm|ng)\b", raw_lc, re.IGNORECASE):
                params["order_by"] = {"field": "defect_count", "direction": "desc"}
            elif re.search(r"\b(actual|thực\s*tế|thuc\s*te)\b", raw_lc, re.IGNORECASE):
                params["order_by"] = {"field": "actual_production_qty", "direction": "desc"}

        # If query is about defect symptom breakdown with "nhiều nhất"/"most", auto-sort by defect_count
        if "order_by" not in params:
            if params.get("group_by") and isinstance(params.get("group_by"), list) and "symptom" in params["group_by"]:
                if re.search(r"\b(nhiều\s*nhất|nhieu\s*nhat|most|highest|top)\b", raw_lc, re.IGNORECASE):
                    params["order_by"] = {"field": "defect_count", "direction": "desc"}
                    params.setdefault("limit", 10)  # Default to top 10 if not specified
                    import logging
                    logging.getLogger(__name__).info(f"Auto-sorting symptom breakdown by defect_count desc with limit 10")

        # Default entity to production if we have time range but no explicit entity
        # This handles queries like "kiểm tra từ tháng 9 đến tháng 12"
        entity_str = str(intent.get("entity", "")).strip()
        is_empty_entity = entity_str in ("", "None") or re.search(r"(từ|from|đến|to|tháng|month|năm|year|/|\d{4})", entity_str, re.IGNORECASE)
        
        # Override entity to "defect" if query is about defect breakdown (symptom)
        # E.g., "lỗi nào nhiều nhất" should query defect entity, not production
        if params.get("group_by") and isinstance(params.get("group_by"), list) and "symptom" in params["group_by"]:
            intent["entity"] = "defect"
            import logging
            logging.getLogger(__name__).info(f"Overriding entity to 'defect' for symptom breakdown query")
        elif is_empty_entity:
            if params.get("time_range") or params.get("from") or params.get("to"):
                intent["entity"] = "production"
                import logging
                logging.getLogger(__name__).info(f"Defaulting entity to 'production' for time range query (was: '{entity_str}')")

        out = {
            "intent": intent.get("intent"),
            "entity": intent.get("entity"),
            "raw_query": raw,
            "params": params,
        }
        if auth:
            out["auth"] = auth
        return out
