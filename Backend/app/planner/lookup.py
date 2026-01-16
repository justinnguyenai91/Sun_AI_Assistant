import os
import logging
try:
    import yaml
except Exception:
    yaml = None

logger = logging.getLogger(__name__)

_lookup = None

def _load():
    global _lookup
    if _lookup is not None:
        return _lookup
    path = os.path.join(os.path.dirname(__file__), "..", "config", "lookup.yaml")
    if yaml is None:
        logger.warning("PyYAML not installed; lookup labels unavailable")
        _lookup = {}
        return _lookup
    try:
        with open(path, "r", encoding="utf-8") as f:
            _lookup = yaml.safe_load(f) or {}
    except Exception as e:
        logger.exception("Failed to load lookup.yaml: %s", e)
        _lookup = {}
    return _lookup

def get_prod_status_label(code: str) -> str:
    data = _load().get("prod_status", {})
    return data.get(code, code)

def get_process_type_label(code: str) -> str:
    data = _load().get("process_type", {})
    return data.get(code, code)
