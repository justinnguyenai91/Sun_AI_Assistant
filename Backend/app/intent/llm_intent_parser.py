import logging
from typing import Any, Dict, Optional

import re
import unicodedata

logger = logging.getLogger(__name__)



class LLMIntentParser:
    """
    Parse natural language query into semantic intent JSON.

    Responsibilities:
    - Try rule-based parsing first
    - Fallback to LLM-based parsing if enabled

    Constraints:
    - No metric / KPI logic
    - No database access
    - LLM is auxiliary only
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        enable_llm: bool = True,
    ):
        self.llm_client = llm_client
        self.enable_llm = enable_llm

    # ============================================================
    # Public API
    # ============================================================

    async def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into semantic intent JSON.
        """

        logger.info("IntentParser.start", extra={"query": query})

        # 1. Rule-based parsing (primary)
        intent = self._rule_based_parse(query)
        if intent is not None:
            logger.debug("IntentParser.rule_based.hit", extra={"intent": intent})
            return intent

        # 2. LLM-based parsing (fallback)
        if self.enable_llm and self.llm_client is not None:
            try:
                intent = await self._llm_parse(query)
                logger.debug("IntentParser.llm.used", extra={"intent": intent})
                return intent
            except Exception as e:
                # Never hard-fail the whole /analyze path due to LLM availability.
                logger.warning("IntentParser.llm.failed: %s", e)

        # 3. Hard fallback
        logger.warning("IntentParser.fallback.default")
        return self._default_intent(query)

    # ============================================================
    # Rule-based parsing
    # ============================================================

    def _rule_based_parse(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Deterministic rule-based intent parsing.
        Simple, explicit, debuggable.
        """

        q = query.lower().strip()

        def _strip_accents(s: str) -> str:
            try:
                nfkd = unicodedata.normalize("NFD", s)
                return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
            except Exception:
                return s

        q_ascii = _strip_accents(q)

        # Report/statistics intent (vi/en/ko) to reduce reliance on LLM correctness.
        # Include KPI/rate-style queries that do not explicitly say "report".
        is_reportish = bool(
            re.search(
                r"(thống\s*kê|báo\s*cáo|report|statistic|statistics|stats|analytics|통계|보고서|sản\s*lượng|năng\s*suất|productivity|production\s*(output)?|output|생산량|생산|yield|tỷ\s*lệ|ti\s*lệ|ty\s*le|rate|ratio|achievement|attainment|đạt\s*kế\s*hoạch|dat\s*ke\s*hoach|pareto|top\s*\d+|bottom\s*\d+|worst\s*\d+)",
                q,
            )
            or re.search(
                r"(thong\s*ke|bao\s*cao|report|statistic|statistics|stats|analytics|san\s*luong|nang\s*suat|productivity|production\s*(output)?|output|yield|ti\s*le|ty\s*le|rate|ratio|achievement|attainment|dat\s*ke\s*hoach|pareto|top\s*\d+|bottom\s*\d+|worst\s*\d+)",
                q_ascii,
            )
            or re.search(r"(defect|lỗi|loi|불량|\bppm\b)", q)
            or re.search(r"(defect|loi|\bppm\b)", q_ascii)
        )

        if is_reportish:
            entity: Optional[str] = None
            # Prefer defect when query includes defect/ppm terms.
            if re.search(r"(defect|lỗi|loi|불량|\bppm\b)", q) or re.search(r"(defect|loi|\bppm\b)", q_ascii):
                entity = "defect"
            elif re.search(
                r"(sản\s*lượng|năng\s*suất|productivity|production\s*(output)?|output|생산량|생산)",
                q,
            ) or re.search(r"(san\s*luong|nang\s*suat|productivity|production\s*(output)?|output)", q_ascii):
                entity = "sản lượng"
            elif re.search(r"(yield|tỷ\s*lệ|ti\s*lệ|ty\s*le|rate|ratio|achievement|attainment|đạt\s*kế\s*hoạch|dat\s*ke\s*hoach)", q) or re.search(
                r"(yield|ti\s*le|ty\s*le|rate|ratio|achievement|attainment|dat\s*ke\s*hoach)",
                q_ascii,
            ):
                # KPI queries are typically production-domain unless they are explicitly defect-related.
                entity = "sản lượng"

            return {
                "intent": "report",
                "entity": entity,
                "raw_query": query,
                "source": "rule_based",
            }

        # Example rule: simple list intent
        if q.startswith("list ") or q.startswith("show "):
            return {
                "intent": "list",
                "entity": self._extract_entity(q),
                "source": "rule_based",
            }

        # Example rule: count intent
        if q.startswith("count "):
            return {
                "intent": "count",
                "entity": self._extract_entity(q),
                "source": "rule_based",
            }

        return None

    def _extract_entity(self, query: str) -> Optional[str]:
        """
        Minimal entity extraction.
        No domain assumptions.
        """
        parts = query.split()
        return parts[-1] if len(parts) > 1 else None

    # ============================================================
    # LLM-based parsing (auxiliary)
    # ============================================================

    async def _llm_parse(self, query: str) -> Dict[str, Any]:
        """
        LLM-assisted intent parsing.
        LLM output MUST be normalized.
        """

        prompt = self._build_prompt(query)

        llm_response = await self.llm_client.complete(prompt)

        return self._normalize_llm_output(llm_response)

    def _build_prompt(self, query: str) -> str:
        """
        Build prompt for LLM. Yêu cầu trả về đúng format chuẩn.
        """
        return (
            "You are an intent parser. Parse the following user query into a JSON object with this exact format: "
            '{"intent": <string>, "entity": <string|null>, "raw_query": <string>}'
            "\n- 'intent': the action or intent (e.g. 'list', 'count', 'report', ...)."
            "\n- 'entity': the main object or subject (e.g. 'sản lượng', 'line', ...), or null if not found."
            "\n- 'raw_query': copy the original user query."
            "\nDo NOT add extra fields. Do NOT infer business logic."
            f"\nQuery: {query}\nReturn JSON only."
        )

    def _normalize_llm_output(self, output: Any) -> Dict[str, Any]:
        """
        Normalize LLM output into expected intent schema.
        Nếu output là chuỗi JSON, parse sang dict.
        """
        import json
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except Exception as e:
                logger.warning("IntentParser.llm.json_parse_error: %s", e)
                return self._default_intent(str(output))
        if isinstance(output, dict) and "intent" in output:
            output["source"] = "llm"
            return output
        # Nếu LLM trả về JSON không đúng format, fallback an toàn
        logger.warning("IntentParser.llm.invalid_output: %s", output)
        return self._default_intent(str(output))

    # ============================================================
    # Default fallback
    def _default_intent(self, query: str) -> Dict[str, Any]:
        """
        Last-resort fallback intent.
        """
        return {
            "intent": "unknown",
            "raw_query": query,
            "source": "fallback",
        }
    # ============================================================
