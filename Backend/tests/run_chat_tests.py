import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import yaml


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


def _get_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


@dataclass
class CaseResult:
    case_id: str
    title: str
    ok: bool
    status_code: int | None
    warnings: list[str]
    errors: list[str]
    elapsed_seconds: float


def _validate_response(case: dict, resp: httpx.Response) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []

    expect = case.get("expect") or {}

    exp_status = expect.get("status_code")
    if isinstance(exp_status, int) and resp.status_code != exp_status:
        errors.append(f"Expected status_code={exp_status}, got {resp.status_code}")
        return warnings, errors

    try:
        body = resp.json()
    except Exception:
        errors.append("Response is not JSON")
        return warnings, errors

    for p in expect.get("json_paths_exist") or []:
        if not isinstance(p, str) or not p.strip():
            continue
        if _get_path(body, p) is None:
            errors.append(f"Missing json path: {p}")

    data = _get_path(body, "planner_result.data")
    if data is None:
        return warnings, errors

    min_rows = expect.get("min_rows")
    if isinstance(min_rows, int):
        if not isinstance(data, list):
            errors.append("planner_result.data is not a list")
        elif len(data) < min_rows:
            errors.append(f"Expected at least {min_rows} rows, got {len(data)}")

    # Optional columns: warn (not fail) if rows exist but columns are missing.
    optional_cols = [str(x) for x in (expect.get("optional_columns") or []) if str(x).strip()]
    if optional_cols and isinstance(data, list) and len(data) > 0:
        keys = set()
        for r in data:
            if isinstance(r, dict):
                keys.update(r.keys())
        for c in optional_cols:
            if c not in keys:
                warnings.append(f"Optional column not present: {c}")

    required_cols = [str(x) for x in (expect.get("required_columns") or []) if str(x).strip()]
    if required_cols and isinstance(data, list) and len(data) > 0:
        keys = set()
        for r in data:
            if isinstance(r, dict):
                keys.update(r.keys())
        for c in required_cols:
            if c not in keys:
                errors.append(f"Missing required column: {c}")

    return warnings, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run chat-style /analyze test cases and write a transcript log.")
    parser.add_argument("--cases", default=os.path.join(os.path.dirname(__file__), "chat_test_cases.yaml"))
    parser.add_argument("--out", default=None, help="Output log file path. Default: Backend/tests/chat_test_log_<timestamp>.txt")
    parser.add_argument("--only", default=None, help="Run only a single case id")
    parser.add_argument("--base-url", default=os.getenv("SUN_ANALYZE_BASE_URL", "http://localhost:9000"))
    parser.add_argument("--api-key", default=os.getenv("SUN_API_KEY", "dev-key-123"))
    parser.add_argument("--timeout", type=float, default=None)

    args = parser.parse_args()

    with open(args.cases, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}

    meta = doc.get("meta") or {}
    cases = doc.get("cases") or []
    if not isinstance(cases, list) or not cases:
        print("No cases found.")
        return 2

    if args.only:
        cases = [c for c in cases if str(c.get("id")) == args.only]
        if not cases:
            print(f"No case matched --only {args.only}")
            return 2

    timeout = args.timeout
    if timeout is None:
        try:
            timeout = float(meta.get("default_timeout_seconds") or 60)
        except Exception:
            timeout = 60

    out_path = args.out
    if not out_path:
        out_path = os.path.join(os.path.dirname(__file__), f"chat_test_log_{_now_stamp()}.txt")

    analyze_url = args.base_url.rstrip("/") + "/analyze"

    results: list[CaseResult] = []

    with open(out_path, "w", encoding="utf-8") as log:
        log.write("CHAT TEST RUN\n")
        log.write(f"Started: {datetime.now().isoformat(timespec='seconds')}\n")
        log.write(f"Analyze URL: {analyze_url}\n")
        log.write(f"Cases file: {os.path.abspath(args.cases)}\n")
        log.write("\n")

        headers = {"Authorization": f"Bearer {args.api_key}", "Content-Type": "application/json"}

        with httpx.Client(timeout=timeout) as client:
            for idx, case in enumerate(cases, start=1):
                case_id = str(case.get("id") or f"case_{idx}")
                title = str(case.get("title") or "")
                prompt = case.get("input")
                context = case.get("context") or {}

                log.write("=" * 80 + "\n")
                log.write(f"CASE {idx}/{len(cases)}: {case_id}\n")
                if title:
                    log.write(f"Title: {title}\n")
                log.write(f"User: {prompt}\n")
                log.write("\n")

                started = time.time()
                status_code: int | None = None
                warnings: list[str] = []
                errors: list[str] = []

                try:
                    resp = client.post(analyze_url, headers=headers, json={"input": prompt, "context": context})
                    status_code = resp.status_code
                    warnings, errors = _validate_response(case, resp)

                    log.write(f"HTTP {resp.status_code}\n")
                    try:
                        body = resp.json()
                        log.write("Assistant (JSON):\n")
                        log.write(_safe_json(body))
                        log.write("\n")
                    except Exception:
                        log.write("Assistant: <non-JSON response>\n")
                        log.write(resp.text[:8000] + ("\n...<truncated>\n" if len(resp.text) > 8000 else "\n"))

                except Exception as e:
                    errors.append(f"Request failed: {e.__class__.__name__}: {e}")

                elapsed = time.time() - started

                ok = len(errors) == 0
                if warnings:
                    log.write("Warnings:\n")
                    for w in warnings:
                        log.write(f"- {w}\n")
                if errors:
                    log.write("Errors:\n")
                    for er in errors:
                        log.write(f"- {er}\n")

                log.write(f"Result: {'PASS' if ok else 'FAIL'} ({elapsed:.2f}s)\n")
                log.write("\n")

                results.append(
                    CaseResult(
                        case_id=case_id,
                        title=title,
                        ok=ok,
                        status_code=status_code,
                        warnings=warnings,
                        errors=errors,
                        elapsed_seconds=elapsed,
                    )
                )

        # Summary
        passed = sum(1 for r in results if r.ok)
        failed = len(results) - passed

        log.write("=" * 80 + "\n")
        log.write("SUMMARY\n")
        log.write(f"Passed: {passed}\n")
        log.write(f"Failed: {failed}\n")
        log.write("\n")
        for r in results:
            log.write(f"- {r.case_id}: {'PASS' if r.ok else 'FAIL'} ({r.elapsed_seconds:.2f}s)\n")
        log.write("\n")
        log.write(f"Finished: {datetime.now().isoformat(timespec='seconds')}\n")

    print(f"Wrote log: {out_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
