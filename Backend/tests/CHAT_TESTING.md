# Chat Testing Automation

This folder supports **chat-style test cases** for the `/analyze` endpoint.

## What this is

- You write test cases as natural-language prompts in [Backend/tests/chat_test_cases.yaml](Backend/tests/chat_test_cases.yaml).
- The runner calls the running backend (`/analyze`) **one-by-one**.
- It validates lightweight expectations (HTTP status, JSON shape, optional/required columns).
- It writes a timestamped transcript-style log file you can review.

## Prerequisites

- Backend is running (for Docker compose: `docker compose up -d --build`).
- You know the API key configured for the backend.

## Run

From repo root:

```powershell
$env:SUN_ANALYZE_BASE_URL = "http://localhost:9000"
$env:SUN_API_KEY = "dev-key-123"
python Backend/tests/run_chat_tests.py
```

Output (example):

- `Backend/tests/chat_test_log_20260115_210102.txt`

## Run a single case

```powershell
python Backend/tests/run_chat_tests.py --only productivity_by_line_2026_01_01_2026_01_15
```

## Add/modify test cases

Edit [Backend/tests/chat_test_cases.yaml](Backend/tests/chat_test_cases.yaml).

Each case supports:

- `input`: the natural language prompt
- `context`: optional context sent to backend
- `expect`:
  - `status_code`: expected HTTP status
  - `json_paths_exist`: list of JSON paths that must exist
  - `min_rows`: minimum number of rows in `planner_result.data`
  - `required_columns`: if rows exist, fail if missing
  - `optional_columns`: if rows exist, warn if missing

## Notes

- Expectations are intentionally kept **stable** (avoid strict row counts) because live MES data changes.
- If you want stricter checks (e.g., specific group-by fields always present), add `required_columns`.
