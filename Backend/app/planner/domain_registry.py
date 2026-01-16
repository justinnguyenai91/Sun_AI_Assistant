from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc if isinstance(doc, dict) else {}


@dataclass(frozen=True)
class _Matcher:
    canonical: str
    pattern: re.Pattern


def _compile_synonyms(mapping: Dict[str, Any]) -> List[_Matcher]:
    matchers: List[_Matcher] = []
    for _, spec in (mapping or {}).items():
        canonical = str(spec.get("canonical") or "").strip()
        if not canonical:
            continue
        synonyms = spec.get("synonyms") or []
        parts: List[str] = []
        for s in synonyms:
            s = str(s or "").strip().lower()
            if not s:
                continue
            parts.append(re.escape(s))
        if not parts:
            continue
        # word-boundary where it helps; keep flexible for non-latin tokens
        pat = re.compile(r"(?:^|\b)(%s)(?:\b|$)" % "|".join(parts), re.IGNORECASE)
        matchers.append(_Matcher(canonical=canonical, pattern=pat))
    return matchers


class DomainRegistry:
    """Config-driven domain registry for entity/action/group-by parsing.

    Designed to be extended by editing YAML files (text changes) rather than adding code.
    """

    def __init__(self, ontology_path: Optional[str] = None):
        root = Path(__file__).resolve().parents[1]  # Backend/app
        default_path = root / "config" / "ontology.yaml"
        path = Path(ontology_path) if ontology_path else default_path
        self._doc = _read_yaml(path)

        self._entity_matchers = _compile_synonyms(self._doc.get("entities") or {})
        self._action_matchers = _compile_synonyms(self._doc.get("actions") or {})
        self._dimension_matchers = _compile_synonyms(self._doc.get("dimensions") or {})
        self._metric_matchers = _compile_synonyms(self._doc.get("metrics") or {})

    def canonical_entity(self, text: str | None, fallback: str | None = None) -> Optional[str]:
        t = (text or "").strip().lower()
        if not t:
            return fallback
        for m in self._entity_matchers:
            if m.pattern.search(t):
                return m.canonical
        return fallback

    def canonical_action(self, text: str | None, fallback: str | None = None) -> Optional[str]:
        t = (text or "").strip().lower()
        if not t:
            return fallback
        for m in self._action_matchers:
            if m.pattern.search(t):
                return m.canonical
        return fallback

    def parse_group_by(self, text: str | None) -> List[str]:
        t = (text or "").strip().lower()
        if not t:
            return []

        # Try to focus on the segment after 'theo'/'by'/'per'/'별'
        gb_segment = t
        m = re.search(r"\b(theo|by|per)\b(.+)$", t)
        if m:
            gb_segment = m.group(2)

        dims: List[str] = []
        for matcher in self._dimension_matchers:
            if matcher.pattern.search(gb_segment):
                dims.append(matcher.canonical)

        # Stable order: keep the order defined in ontology.yaml by preserving matcher list order.
        # Remove duplicates while preserving order.
        out: List[str] = []
        seen = set()
        for d in dims:
            if d in seen:
                continue
            seen.add(d)
            out.append(d)
        return out

    def parse_metrics(self, text: str | None) -> List[str]:
        t = (text or "").strip().lower()
        if not t:
            return []

        found: List[str] = []
        for matcher in self._metric_matchers:
            if matcher.pattern.search(t):
                found.append(matcher.canonical)

        # Remove duplicates while preserving order.
        out: List[str] = []
        seen = set()
        for m in found:
            if m in seen:
                continue
            seen.add(m)
            out.append(m)
        return out

    def metric_entity(self, metric_id: str | None) -> Optional[str]:
        mid = str(metric_id or "").strip()
        if not mid:
            return None
        metrics = self._doc.get("metrics")
        if not isinstance(metrics, dict):
            return None
        mdef = metrics.get(mid)
        if not isinstance(mdef, dict):
            return None
        ent = mdef.get("entity")
        if not ent:
            return None
        ent_str = str(ent).strip()
        return ent_str or None


_registry_singleton: Optional[DomainRegistry] = None


def get_registry() -> DomainRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = DomainRegistry()
    return _registry_singleton
