import os
import json
import httpx
import asyncio
import time
from typing import Dict, Any, List
import logging


class ApiDataAdapter:
    """
    Adapter that calls a test MES HTTP API to fetch report data.

    Expects env var `MES_TEST_URL` to point to an endpoint that accepts
    POST requests with the execution plan and returns JSON list of rows.

    This keeps CSV files untouched and exercises the API-first flow.
    """

    def __init__(self, base_url: str | None = None):
        # Use external API config if available (prefer explicit base + prefix)
        env_base = os.getenv("EXTERNAL_API_BASE_URL")
        env_prefix = os.getenv("EXTERNAL_API_PREFIX", "")
        if base_url:
            self.base_url = base_url
        elif env_base:
            # build full URL: base + prefix + /report
            prefix = env_prefix.rstrip("/")
            self.base_url = f"{env_base.rstrip('/')}{prefix}/report"
        else:
            # fallback to legacy test URL
            self.base_url = os.getenv("MES_TEST_URL", "http://mes-test:5000/report")

        # timeout (seconds)
        try:
            self.timeout = int(os.getenv("EXTERNAL_API_TIMEOUT", "60"))
        except Exception:
            self.timeout = 60

        # TLS verification (default true). Set EXTERNAL_API_VERIFY_TLS=false for test.
        v = str(os.getenv("EXTERNAL_API_VERIFY_TLS", "true")).strip().lower()
        self.verify_tls = not (v in ("0", "false", "no", "off"))

        # optional bearer token
        self.bearer = os.getenv("EXTERNAL_API_TOKEN") or os.getenv("MES_API_TOKEN")
        # optional feature code header
        # NOTE: do NOT set a default here. If MES requires a feature code,
        # it must be explicitly provided via EXTERNAL_API_FEATURE_CODE.
        self.feature_code = os.getenv("EXTERNAL_API_FEATURE_CODE")

        # Optional per-factory routing map.
        # Preferred: a single JSON mapping to avoid hardcoding per-factory env var names.
        #   MES_FACTORY_BASE_URLS={"FAC01":"http://10.0.0.1:9082","DJVN1":"http://10.0.0.1:9083"}
        # Backward-compatible: per-factory env vars.
        #   MES_FACTORY_BASE_URL_FAC01=http://10.0.0.1:9082
        self._factory_base_urls: Dict[str, str] = {}

        raw_map = os.getenv("MES_FACTORY_BASE_URLS") or os.getenv("MES_FACTORY_ROUTES")
        if raw_map and isinstance(raw_map, str):
            candidate = raw_map.strip()
            # Allow quoting in .env files
            if (candidate.startswith('"') and candidate.endswith('"')) or (candidate.startswith("'") and candidate.endswith("'")):
                candidate = candidate[1:-1].strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    for code, url in parsed.items():
                        if not isinstance(code, str) or not isinstance(url, str):
                            continue
                        c = code.strip().upper()
                        u = url.strip().rstrip("/")
                        if c and u:
                            self._factory_base_urls[c] = u
            except Exception:
                # Ignore invalid JSON and continue with per-factory env vars
                pass

        for k, v in os.environ.items():
            if not k.startswith("MES_FACTORY_BASE_URL_"):
                continue
            code = k.replace("MES_FACTORY_BASE_URL_", "").strip().upper()
            if code and v:
                self._factory_base_urls[code] = str(v).strip().rstrip("/")

        # Optional per-factory default query params (org hierarchy, line/process lists, etc.)
        # Example:
        #   MES_FACTORY_DEFAULT_PARAMS={"FAC01":{"factoryPks":"FAC01-6","plantPks":"FAC01-1","linePks":"FAC01-1,FAC01-2"}}
        self._factory_default_params: Dict[str, Dict[str, Any]] = {}
        raw_defaults = os.getenv("MES_FACTORY_DEFAULT_PARAMS") or os.getenv("MES_FACTORY_QUERY_DEFAULTS")
        if raw_defaults and isinstance(raw_defaults, str):
            candidate = raw_defaults.strip()
            if (candidate.startswith('"') and candidate.endswith('"')) or (candidate.startswith("'") and candidate.endswith("'")):
                candidate = candidate[1:-1].strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    for code, params in parsed.items():
                        if not isinstance(code, str) or not isinstance(params, dict):
                            continue
                        c = code.strip().upper()
                        if not c:
                            continue
                        self._factory_default_params[c] = params
            except Exception:
                # ignore invalid JSON
                pass

    def _resolve_base_url(self, execution_plan: Dict[str, Any]) -> str | None:
        logger = logging.getLogger(__name__)
        filters = execution_plan.get("filters", {}) or {}
        if isinstance(filters, list):
            filters = next((x for x in filters if isinstance(x, dict)), {})
        elif not isinstance(filters, dict):
            filters = {}

        params = execution_plan.get("params", {}) or {}
        if isinstance(params, list):
            params = next((x for x in params if isinstance(x, dict)), {})
        elif not isinstance(params, dict):
            params = {}
        fc = filters.get("factoryCode") or params.get("factoryCode") or execution_plan.get("factoryCode")
        if isinstance(fc, str) and fc.strip():
            fc_upper = fc.strip().upper()
            base = self._factory_base_urls.get(fc_upper)
            if base:
                logger.info(f"[MES] Resolved base URL for factory {fc_upper}: {base}")
                return base
            else:
                logger.warning(f"[MES] No base URL configured for factory {fc_upper}, available: {list(self._factory_base_urls.keys())}")
        # fallback to global base
        fallback = os.getenv("EXTERNAL_API_BASE_URL")
        logger.info(f"[MES] Using fallback base URL: {fallback} (factoryCode={fc})")
        return fallback

    def _resolve_factory_defaults(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        filters = execution_plan.get("filters", {}) or {}
        if isinstance(filters, list):
            filters = next((x for x in filters if isinstance(x, dict)), {})
        elif not isinstance(filters, dict):
            filters = {}

        params = execution_plan.get("params", {}) or {}
        if isinstance(params, list):
            params = next((x for x in params if isinstance(x, dict)), {})
        elif not isinstance(params, dict):
            params = {}
        fc = filters.get("factoryCode") or params.get("factoryCode") or execution_plan.get("factoryCode")
        if isinstance(fc, str) and fc.strip():
            return dict(self._factory_default_params.get(fc.strip().upper()) or {})
        return {}

    @staticmethod
    def _to_query_value(v: Any) -> Any:
        if v is None:
            return None
        # list -> comma separated
        if isinstance(v, (list, tuple)):
            parts = []
            for x in v:
                if x is None:
                    continue
                s = str(x).strip()
                if s:
                    parts.append(s)
            return ",".join(parts)
        return str(v) if isinstance(v, (str, int, float, bool)) else str(v)

    async def execute(self, execution_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger = logging.getLogger(__name__)
        headers = {"Accept": "application/json"}

        # Per-request token override (service mode): MES calls chatbox and supplies a token.
        bearer = None
        auth = execution_plan.get("auth") if isinstance(execution_plan, dict) else None
        if isinstance(auth, dict):
            bearer = auth.get("mes_token") or auth.get("token")
        if isinstance(bearer, str) and bearer.strip():
            bearer = bearer.strip()
            # Allow passing full "Bearer <token>" or raw token.
            if bearer.lower().startswith("bearer "):
                headers["Authorization"] = bearer
            else:
                headers["Authorization"] = f"Bearer {bearer}"
        elif self.bearer:
            headers["Authorization"] = f"Bearer {self.bearer}"

        # If no token is available, fail fast so callers don't mistake it for "no data".
        if "Authorization" not in headers:
            raise RuntimeError(
                "mes_missing_access_token: set EXTERNAL_API_TOKEN (service mode) or pass context.mesToken (per-request mode)"
            )

        # Feature code can be provided either via env (EXTERNAL_API_FEATURE_CODE)
        # or per-request (filters.featureCode) to support multiple MES permissions.
        filters = execution_plan.get("filters", {}) or {}
        if isinstance(filters, list):
            filters = next((x for x in filters if isinstance(x, dict)), {})
        elif not isinstance(filters, dict):
            filters = {}

        params_in = execution_plan.get("params", {}) or {}
        if isinstance(params_in, list):
            params_in = next((x for x in params_in if isinstance(x, dict)), {})
        elif not isinstance(params_in, dict):
            params_in = {}
        feature_code = (
            filters.get("featureCode")
            or filters.get("feature_code")
            or params_in.get("featureCode")
            or params_in.get("feature_code")
            or execution_plan.get("featureCode")
            or execution_plan.get("feature_code")
            or self.feature_code
        )
        if isinstance(feature_code, str) and feature_code.strip():
            feature_code = feature_code.strip()
        else:
            feature_code = None

        # Some MES gateways require a feature code for authorization.
        # Send a few common header variants to avoid vendor-specific mismatch.
        if feature_code:
            headers.setdefault("Feature-Code", feature_code)
            headers.setdefault("FeatureCode", feature_code)
            headers.setdefault("X-Feature-Code", feature_code)
        retries = int(os.getenv("EXTERNAL_API_RETRIES", "3"))
        # Config-driven routing: prefer explicit method/endpoint from template.
        action = execution_plan.get("action")
        method = (execution_plan.get("method") or "").upper()
        endpoint = execution_plan.get("endpoint")

        def _build_endpoint_url(ep: str) -> str:
            env_base = self._resolve_base_url(execution_plan)
            env_prefix = os.getenv("EXTERNAL_API_PREFIX", "")
            if env_base:
                prefix = env_prefix.rstrip("/")
                return f"{env_base.rstrip('/')}{prefix}{str(ep).strip()}"
            return self.base_url.replace("/report", str(ep).strip())

        def _build_effective_filters() -> Dict[str, Any]:
            from datetime import date, timedelta
            effective: Dict[str, Any] = {}
            for k, v in (self._resolve_factory_defaults(execution_plan) or {}).items():
                if v is None:
                    continue
                effective[str(k)] = v
            filters_local = execution_plan.get("filters", {}) or {}
            if isinstance(filters_local, dict):
                for k, v in filters_local.items():
                    effective[str(k)] = v
            
            # Convert time_range {value, unit} to from/to dates if not already present
            tr = effective.get("time_range")
            if tr and isinstance(tr, dict) and "from" not in effective:
                val = tr.get("value")
                unit = tr.get("unit", "").lower()
                today = date.today()
                if unit.startswith("year") and isinstance(val, int):
                    from_date = today - timedelta(days=365 * val)
                    effective["from"] = from_date.isoformat()
                    effective["to"] = today.isoformat()
                elif unit.startswith("month") and isinstance(val, int):
                    from_date = today - timedelta(days=30 * val)
                    effective["from"] = from_date.isoformat()
                    effective["to"] = today.isoformat()
                elif unit.startswith("week") and isinstance(val, int):
                    from_date = today - timedelta(weeks=val)
                    effective["from"] = from_date.isoformat()
                    effective["to"] = today.isoformat()
                elif unit.startswith("day") and isinstance(val, int):
                    from_date = today - timedelta(days=val)
                    effective["from"] = from_date.isoformat()
                    effective["to"] = today.isoformat()
            
            return effective

        def _apply_fixed_and_mapped(target: Dict[str, Any], effective_filters: Dict[str, Any]):
            fixed = execution_plan.get("fixed_params") or {}
            if isinstance(fixed, dict):
                for k, v in fixed.items():
                    if v is None:
                        continue
                    target[str(k)] = v

            qmap = execution_plan.get("query_params")
            if isinstance(qmap, dict) and qmap:
                for filter_key, qp in qmap.items():
                    if not qp:
                        continue
                    if filter_key not in effective_filters:
                        continue
                    v = effective_filters.get(filter_key)
                    if v is None or (isinstance(v, str) and not v.strip()):
                        continue
                    target[str(qp)] = v
            else:
                for name in execution_plan.get("params") or []:
                    if name in (None, ""):
                        continue
                    if name not in effective_filters:
                        continue
                    v = effective_filters.get(name)
                    if v is None or (isinstance(v, str) and not v.strip()):
                        continue
                    target[str(name)] = v

            if effective_filters.get("from") is not None:
                target["from"] = str(effective_filters.get("from"))
            if effective_filters.get("to") is not None:
                target["to"] = str(effective_filters.get("to"))

            target.pop("factoryCode", None)

        # Template-driven endpoint call (GET/POST)
        if endpoint and method in ("GET", "POST"):
            url = _build_endpoint_url(str(endpoint))
            effective_filters = _build_effective_filters()

            # Build params/body from fixed_params + query_params mapping
            payload: Dict[str, Any] = {}
            params: Dict[str, Any] = {}
            _apply_fixed_and_mapped(payload, effective_filters)

            # For GET we must send query params; for POST default to JSON body.
            if method == "GET":
                for k, v in payload.items():
                    params[str(k)] = self._to_query_value(v)
                if feature_code:
                    params.setdefault("featureCode", feature_code)
            else:
                # Many gateways accept ONLY query params for paging/filtering.
                # Send both: query params (serialized) + JSON body (raw).
                for k, v in payload.items():
                    params[str(k)] = self._to_query_value(v)
                if feature_code:
                    payload.setdefault("featureCode", feature_code)
                    params.setdefault("featureCode", feature_code)

            safe_headers = {
                k: ("Bearer ***" if (k.lower() == "authorization" and v) else v)
                for k, v in headers.items()
            }
            logger.debug(
                "MES %s %s params=%s headers=%s payload=%s",
                method,
                url,
                params,
                safe_headers,
                (payload if method == "POST" else None),
            )
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_tls) as client:
                r = None
                for attempt in range(retries):
                    try:
                        if method == "POST":
                            r = await client.post(url, params=params, json=payload, headers=headers)
                        else:
                            r = await client.get(url, params=params, headers=headers)
                        break
                    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                        logger.warning("MES %s attempt %d failed: %s", method, attempt + 1, e)
                        if attempt + 1 < retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        logger.exception("MES %s failed after retries: %s", method, e)
                        raise
                    except Exception as e:
                        logger.exception("MES %s unexpected error: %s", method, e)
                        return []

            logger.debug("MES response status=%s text=%s", r.status_code, (r.text[:1000] + '...' if len(r.text) > 1000 else r.text))
            if r.status_code != 200:
                safe_headers = {
                    k: ("Bearer ***" if (k.lower() == "authorization" and v) else v)
                    for k, v in headers.items()
                }
                logger.warning(
                    "MES returned non-200: %s %s | url=%s | params=%s | headers=%s",
                    r.status_code,
                    r.text,
                    url,
                    params,
                    safe_headers,
                )
                raise RuntimeError(f"mes_upstream_non_200: status={r.status_code}")
            try:
                data = r.json()
            except Exception as e:
                logger.warning("MES response not JSON: %s", e)
                return []

        elif action == "production_order_search":
            # build URL from EXTERNAL_API_BASE_URL + prefix + /productionOrder/search
            env_base = self._resolve_base_url(execution_plan)
            env_prefix = os.getenv("EXTERNAL_API_PREFIX", "")
            if env_base:
                prefix = env_prefix.rstrip("/")
                url = f"{env_base.rstrip('/')}{prefix}/productionOrder/search"
            else:
                url = self.base_url.replace("/report", "/productionOrder/search")

            # Map filters -> query params. Support explicit from/to or time_range -> from/to
            # Start with no params; only include adapter defaults if explicitly provided via env
            params = {}
            # Do NOT inject global defaults.
            filters = execution_plan.get("filters", {}) or {}
            tr = filters.get("time_range")
            # support explicit 'from'/'to' already present (QueryBuilder may convert time_range)
            explicit_from = filters.get("from")
            explicit_to = filters.get("to")
            if explicit_from or explicit_to:
                if explicit_from:
                    params["from"] = str(explicit_from)
                if explicit_to:
                    params["to"] = str(explicit_to)
            from datetime import date, timedelta
            # support structured time_range {value, unit} or legacy string
            if tr:
                if isinstance(tr, dict):
                    val = tr.get("value")
                    unit = tr.get("unit", "").lower()
                    if unit.startswith("year") and isinstance(val, int):
                        years = val
                        today = date.today()
                        from_date = today - timedelta(days=365 * years)
                        params.setdefault("from", from_date.isoformat())
                        params.setdefault("to", today.isoformat())
                    elif unit.startswith("month") and isinstance(val, int):
                        months = val
                        today = date.today()
                        from_date = today - timedelta(days=30 * months)
                        params.setdefault("from", from_date.isoformat())
                        params.setdefault("to", today.isoformat())
                    elif unit.startswith("week") and isinstance(val, int):
                        weeks = val
                        today = date.today()
                        from_date = today - timedelta(weeks=weeks)
                        params.setdefault("from", from_date.isoformat())
                        params.setdefault("to", today.isoformat())
                    elif unit.startswith("day") and isinstance(val, int):
                        days = val
                        today = date.today()
                        from_date = today - timedelta(days=days)
                        params.setdefault("from", from_date.isoformat())
                        params.setdefault("to", today.isoformat())
                elif isinstance(tr, str) and tr.endswith("_years"):
                    try:
                        years = int(tr.split("_")[0])
                        today = date.today()
                        from_date = today - timedelta(days=365 * years)
                        params.setdefault("from", from_date.isoformat())
                        params.setdefault("to", today.isoformat())
                    except Exception:
                        pass

            # Do NOT send groupBy to MES by default.
            # We fetch raw rows and do grouping/aggregation in backend response phase.

            # Some MES gateways require featureCode as a query param (not only header)
            if feature_code:
                params.setdefault("featureCode", feature_code)

            # (defaults already merged above if present)

            # Planning filters
            if filters.get("poType"):
                params["poType"] = str(filters.get("poType"))

            # NOTE: factoryCode is used only for routing base URL; do not send as a query param.

            safe_headers = {
                k: ("Bearer ***" if (k.lower() == "authorization" and v) else v)
                for k, v in headers.items()
            }
            logger.debug("MES GET %s params=%s headers=%s", url, params, safe_headers)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = None
                for attempt in range(retries):
                    try:
                        r = await client.get(url, params=params, headers=headers)
                        break
                    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                        logger.warning("MES GET attempt %d failed: %s", attempt + 1, e)
                        if attempt + 1 < retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        logger.exception("MES GET failed after retries: %s", e)
                        raise
                    except Exception as e:
                        logger.exception("MES GET unexpected error: %s", e)
                        return []

            logger.debug("MES response status=%s text=%s", r.status_code, (r.text[:1000] + '...' if len(r.text) > 1000 else r.text))
            if r.status_code != 200:
                safe_headers = {
                    k: ("Bearer ***" if (k.lower() == "authorization" and v) else v)
                    for k, v in headers.items()
                }
                logger.warning(
                    "MES returned non-200: %s %s | url=%s | params=%s | headers=%s",
                    r.status_code,
                    r.text,
                    url,
                    params,
                    safe_headers,
                )
                # Handle 404 gracefully - no data available
                if r.status_code == 404:
                    logger.info("MES API returned 404 - no data available for query")
                    return []
                raise RuntimeError(f"mes_upstream_non_200: status={r.status_code}")
            try:
                data = r.json()
            except Exception as e:
                logger.warning("MES response not JSON: %s", e)
                return []

        else:
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_tls) as client:
                r = None
                payload = dict(execution_plan or {})
                # Some MES gateways expect featureCode in body.
                if feature_code:
                    payload.setdefault("featureCode", feature_code)
                for attempt in range(retries):
                    try:
                        safe_headers = {
                            k: ("Bearer ***" if (k.lower() == "authorization" and v) else v)
                            for k, v in headers.items()
                        }
                        logger.debug("MES request to %s headers=%s payload=%s", self.base_url, safe_headers, payload)
                        r = await client.post(self.base_url, json=payload, headers=headers)
                        break
                    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                        logger.warning("MES POST attempt %d failed: %s", attempt + 1, e)
                        if attempt + 1 < retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        logger.exception("MES POST failed after retries: %s", e)
                        raise
                    except Exception as e:
                        logger.exception("MES request failed: %s", e)
                        return []

            logger.debug("MES response status=%s text=%s", r.status_code, (r.text[:1000] + '...' if len(r.text) > 1000 else r.text))
            if r.status_code != 200:
                safe_headers = {
                    k: ("Bearer ***" if (k.lower() == "authorization" and v) else v)
                    for k, v in headers.items()
                }
                logger.warning(
                    "MES returned non-200: %s %s | url=%s | headers=%s",
                    r.status_code,
                    r.text,
                    self.base_url,
                    safe_headers,
                )
                # Handle 404 gracefully - no data available
                if r.status_code == 404:
                    logger.info("MES API returned 404 - no data available for query")
                    return []
                raise RuntimeError(f"mes_upstream_non_200: status={r.status_code}")

            try:
                data = r.json()
            except Exception as e:
                logger.warning("MES response not JSON: %s", e)
                return []
        # If the API returns a wrapper, try to normalize to a list of rows.
        # Some MES endpoints return: { data: [...] }
        # Others return: { data: { content: [...], pageable: {...}, ... } }
        if isinstance(data, dict) and "data" in data:
            inner = data.get("data")
            if isinstance(inner, list):
                logger.debug("MES returned data list rows count=%d", len(inner))
                if str(os.getenv("MES_DEBUG_ROWS", "")).strip().lower() in ("1", "true", "yes", "on"):
                    logger.info(
                        "MES.rows",
                        extra={
                            "endpoint": endpoint,
                            "method": method,
                            "row_count": len(inner),
                        },
                    )
                return inner
            if isinstance(inner, dict):
                if isinstance(inner.get("content"), list):
                    rows = inner.get("content")
                    logger.debug("MES returned data.content rows count=%d", len(rows))
                    if str(os.getenv("MES_DEBUG_ROWS", "")).strip().lower() in ("1", "true", "yes", "on"):
                        logger.info(
                            "MES.rows",
                            extra={
                                "endpoint": endpoint,
                                "method": method,
                                "row_count": len(rows),
                            },
                        )
                    return rows
                if isinstance(inner.get("rows"), list):
                    rows = inner.get("rows")
                    logger.debug("MES returned data.rows rows count=%d", len(rows))
                    if str(os.getenv("MES_DEBUG_ROWS", "")).strip().lower() in ("1", "true", "yes", "on"):
                        logger.info(
                            "MES.rows",
                            extra={
                                "endpoint": endpoint,
                                "method": method,
                                "row_count": len(rows),
                            },
                        )
                    return rows
            logger.warning("MES returned unexpected 'data' wrapper type: %s", type(inner))
            return []

        # Spring Data pageable wrapper at top level
        if isinstance(data, dict) and "content" in data:
            rows = data.get("content")
            logger.debug("MES returned content rows count=%d", len(rows) if isinstance(rows, list) else 0)
            if isinstance(rows, list) and str(os.getenv("MES_DEBUG_ROWS", "")).strip().lower() in ("1", "true", "yes", "on"):
                logger.info(
                    "MES.rows",
                    extra={
                        "endpoint": endpoint,
                        "method": method,
                        "row_count": len(rows),
                    },
                )
            return rows if isinstance(rows, list) else []

        if isinstance(data, dict) and "rows" in data:
            rows = data.get("rows")
            logger.debug("MES returned rows count=%d", len(rows) if isinstance(rows, list) else 0)
            if isinstance(rows, list) and str(os.getenv("MES_DEBUG_ROWS", "")).strip().lower() in ("1", "true", "yes", "on"):
                logger.info(
                    "MES.rows",
                    extra={
                        "endpoint": endpoint,
                        "method": method,
                        "row_count": len(rows),
                    },
                )
            return rows if isinstance(rows, list) else []
        if isinstance(data, list):
            logger.debug("MES returned list rows count=%d", len(data))
            if str(os.getenv("MES_DEBUG_ROWS", "")).strip().lower() in ("1", "true", "yes", "on"):
                logger.info(
                    "MES.rows",
                    extra={
                        "endpoint": endpoint,
                        "method": method,
                        "row_count": len(data),
                    },
                )
            
            # ============================================================
            # POST-PROCESSING: Enrich defect data with line info from PO
            # ============================================================
            # If this is a defect query that needs line grouping, but defect API
            # doesn't return line info, join with production order data via PO number.
            await self._enrich_defect_with_line_info(execution_plan, data, headers)
            
            return data

        logger.warning("MES returned unexpected JSON structure: %s", type(data))
        return []

    async def _enrich_defect_with_line_info(
        self, 
        execution_plan: Dict[str, Any], 
        defect_rows: List[Dict[str, Any]], 
        headers: Dict[str, str]
    ) -> None:
        """
        Enrich defect data with line information from production order API.
        
        Defect API (/process-defect/search-v2) doesn't include line info,
        but production order API does. We join via PO number and factory code.
        
        This method modifies defect_rows in-place.
        """
        if not defect_rows:
            return
        
        # Check if this is a defect query that needs line enrichment
        endpoint = execution_plan.get("endpoint", "")
        group_by = execution_plan.get("group_by") or []
        if not isinstance(group_by, list):
            group_by = [group_by] if group_by else []
        
        # Only enrich if:
        # 1. This is a defect endpoint
        # 2. User requested group by line (or model/process that also need PO data)
        if "/process-defect/search" not in endpoint and "/processDefect/search" not in endpoint:
            return
        
        needs_enrichment = any(dim in group_by for dim in ["line", "model", "process"])
        if not needs_enrichment:
            return
        
        # Extract unique PO numbers from defect data
        po_field_candidates = [
            "processDefect.productionOrder.code",
            "processDefect.productionOrder.poCode", 
            "processDefect.poCode",
            "productionOrder.code",
            "productionOrder.poCode",
            "poCode",
            "po_code",
            "po",
            "productionOrderCode"
        ]
        
        po_numbers = set()
        for row in defect_rows:
            for field in po_field_candidates:
                val = self._get_nested_value(row, field)
                if val and isinstance(val, str):
                    po_numbers.add(val)
                    break
        
        if not po_numbers:
            logger.debug("No PO numbers found in defect data, cannot enrich with line info")
            return
        
        logger.info(f"Enriching {len(defect_rows)} defect rows with line info from {len(po_numbers)} POs")
        
        # Query production order API to get line info for these POs
        filters = execution_plan.get("filters", {}) or {}
        factory_code = filters.get("factoryCode") or filters.get("factory_code")
        
        # Build PO search request
        po_url = self._build_po_search_url(execution_plan)
        po_params = {
            "pageSize": 1000,
            "pageNumber": 0
        }
        
        # Add factory filter if available
        if factory_code:
            # Try both factoryPk (singular) and factoryPks (plural)
            po_params["factoryPk"] = factory_code
        
        # Query for specific PO codes (if API supports it)
        # Note: Some MES APIs support poCodes filter, others require fetching all and filtering
        po_list = ",".join(sorted(po_numbers)[:100])  # Limit to first 100 POs to avoid URL length issues
        po_params["poCodes"] = po_list
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Fetching PO data from {po_url} with params={po_params}")
                r = await client.get(po_url, params=po_params, headers=headers)
                
                if r.status_code != 200:
                    logger.warning(f"PO API returned {r.status_code}, cannot enrich defect data")
                    return
                
                po_data = r.json()
                
                # Extract PO rows from response
                po_rows = []
                if isinstance(po_data, dict) and "data" in po_data:
                    inner = po_data.get("data")
                    if isinstance(inner, list):
                        po_rows = inner
                    elif isinstance(inner, dict):
                        po_rows = inner.get("content") or inner.get("rows") or []
                elif isinstance(po_data, dict) and "content" in po_data:
                    po_rows = po_data.get("content", [])
                elif isinstance(po_data, list):
                    po_rows = po_data
                
                if not po_rows:
                    logger.warning("No PO data returned from production order API")
                    return
                
                # Build PO number -> line info mapping
                po_to_line_map = {}
                for po_row in po_rows:
                    po_code = (
                        po_row.get("poCode") or 
                        po_row.get("po_code") or 
                        po_row.get("code") or
                        po_row.get("productionOrderCode")
                    )
                    if not po_code:
                        continue
                    
                    # Extract line info from PO row
                    line_info = {
                        "lineCode": (
                            self._get_nested_value(po_row, "line.code") or
                            po_row.get("lineCode") or
                            po_row.get("line_code")
                        ),
                        "lineName": (
                            self._get_nested_value(po_row, "line.name") or
                            po_row.get("lineName") or
                            po_row.get("line_name")
                        ),
                        "modelCode": (
                            self._get_nested_value(po_row, "model.code") or
                            po_row.get("modelCode") or
                            po_row.get("model_code")
                        ),
                        "modelName": (
                            self._get_nested_value(po_row, "model.name") or
                            po_row.get("modelName") or
                            po_row.get("model_name")
                        ),
                        "processTypeCode": (
                            self._get_nested_value(po_row, "process.code") or
                            po_row.get("processTypeCode") or
                            po_row.get("process_code")
                        ),
                        "processTypeName": (
                            self._get_nested_value(po_row, "process.name") or
                            po_row.get("processTypeName") or
                            po_row.get("process_name")
                        )
                    }
                    po_to_line_map[po_code] = line_info
                
                logger.info(f"Built PO -> line mapping with {len(po_to_line_map)} entries")
                
                # Enrich defect rows with line info
                enriched_count = 0
                for row in defect_rows:
                    # Find PO code in defect row
                    po_code = None
                    for field in po_field_candidates:
                        val = self._get_nested_value(row, field)
                        if val and isinstance(val, str):
                            po_code = val
                            break
                    
                    if not po_code or po_code not in po_to_line_map:
                        continue
                    
                    # Merge line info into defect row
                    line_info = po_to_line_map[po_code]
                    for key, value in line_info.items():
                        if value and key not in row:
                            row[key] = value
                    enriched_count += 1
                
                logger.info(f"Enriched {enriched_count}/{len(defect_rows)} defect rows with line info")
                
        except Exception as e:
            logger.warning(f"Failed to enrich defect data with line info: {e}", exc_info=True)
            # Don't fail the whole query if enrichment fails
            return
    
    def _build_po_search_url(self, execution_plan: Dict[str, Any]) -> str:
        """Build production order search URL based on base URL configuration."""
        env_base = self._resolve_base_url(execution_plan)
        env_prefix = os.getenv("EXTERNAL_API_PREFIX", "")
        if env_base:
            prefix = env_prefix.rstrip("/")
            return f"{env_base.rstrip('/')}{prefix}/productionOrder/search"
        else:
            return self.base_url.replace("/report", "/productionOrder/search")
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value from dict using dot notation (e.g., 'line.code')."""
        if not isinstance(obj, dict):
            return None
        keys = path.split(".")
        value = obj
        for key in keys:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
            if value is None:
                return None
        return value

