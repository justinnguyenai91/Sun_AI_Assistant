# Memory + Defaults Spec (Session-first, Vector later)

This describes how the assistant should remember context and personalize defaults **per user**, without vector DB initially.

## 1) Memory layers

### Layer A — Session State (required now)
Purpose: deterministic continuity (last factory/grouping/metrics/time mode).

- Storage: Postgres JSONB (simple) or Redis (fast).
- Key: `(user_id, session_id)`
- Updated after every successful `report` request.

Recommended state keys:
- `locale`
- `factoryCodes`
- `last_intent` / `last_entity`
- `last_group_by`
- `last_metrics`
- `last_time`: `{mode, from, to}`
- `last_bundle_id`

### Layer B — Event Log (required now)
Purpose: audit + replay + debugging + future embeddings.

- Storage: Postgres table
- Append-only (never update in place; add a new row per request)

### Layer C — Semantic Memory / Vector DB (later)
Purpose: fuzzy recall of prior reports (“same report as before”, “rotor report again”).

- Storage: pgvector or Qdrant
- Sources for embeddings:
  - `user_text`
  - `semantic_request` (normalized, stable)
  - `selected_template_ids`

Vector DB is a **candidate generator**, not source of truth.

## 2) Postgres schema (DDL)

### 2.1 session_state

```sql
create table if not exists assistant_session_state (
  user_id text not null,
  session_id text not null,
  updated_at timestamptz not null default now(),
  state jsonb not null,
  primary key (user_id, session_id)
);

create index if not exists idx_session_state_updated_at
  on assistant_session_state(updated_at desc);
```

Example `state` JSON:
```json
{
  "locale": "vi",
  "factoryCodes": ["DJVN1"],
  "last_bundle_id": "current_production",
  "last_entity": "production",
  "last_group_by": ["date", "line"],
  "last_metrics": ["plan_qty", "actual_production_qty", "achievement_rate"],
  "last_time": {"mode": "iso_last_week", "from": "2026-01-05", "to": "2026-01-11"}
}
```

### 2.2 event_log

```sql
create table if not exists assistant_event_log (
  id bigserial primary key,
  ts timestamptz not null default now(),
  user_id text not null,
  session_id text not null,
  user_text text not null,
  locale text,
  semantic_request jsonb,
  execution_plan jsonb,
  result_summary jsonb,
  error jsonb
);

create index if not exists idx_event_user_session_ts
  on assistant_event_log(user_id, session_id, ts desc);

create index if not exists idx_event_ts
  on assistant_event_log(ts desc);
```

Recommended `result_summary`:
```json
{
  "rows": 42,
  "columns": ["date","lineCode","actual_production_qty","plan_qty","achievement_rate"],
  "template_ids": ["kpi.actual_qty.daily", "kpi.plan_qty.daily"]
}
```

## 3) Per-user defaults

### 3.1 user_defaults table

```sql
create table if not exists assistant_user_defaults (
  user_id text primary key,
  updated_at timestamptz not null default now(),
  defaults jsonb not null
);
```

Example `defaults` JSON:
```json
{
  "timezone_offset_hours": 7,
  "default_factoryCodes": ["DJVN1"],
  "bundles": {
    "current_production": {
      "entity": "production",
      "group_by": ["date","line"],
      "metrics": ["plan_qty","actual_production_qty","achievement_rate"],
      "time_mode": "iso_last_week"
    }
  }
}
```

## 4) Mapping rules (NLU v1)

### 4.1 Intent/entity cues (VN + EN)

- **Production/current production** → entity `production`
  - EN: "current production", "production status", "output", "plan achievement"
  - VI: "tình hình sản xuất", "sản lượng", "tiến độ", "đạt kế hoạch"

- **Defect** → entity `defect`
  - EN: "defect", "ppm", "reject", "NG"
  - VI: "lỗi", "PPM", "phế", "NG"

### 4.2 Time cues

- `last week` / `tuần rồi` / `tuần trước` → `time.mode=iso_last_week`
- `this week` / `tuần này` → `time.mode=iso_this_week`
- explicit dates `YYYY-MM-DD` or `from ... to ...` → `absolute_range`

### 4.3 Bundle selection (per-user)

When message contains:
- production cues + time cue + no explicit metrics → select bundle `current_production`

### 4.4 Group-by defaults

If no explicit grouping provided and bundle is `current_production`:
- `group_by=["date","line"]`

If user explicitly requests:
- “by shift / theo ca” → include `shift`
- “by model / theo model” → include `model`

## 5) When to add vector DB (later)

Add semantic retrieval when you need these capabilities:
- “Same report as last time” / “giống lần trước”
- “the rotor report” / “báo cáo rotor”
- “that table from yesterday”

Plan:
1) Store event_log first.
2) When ready, embed the last N successful semantic_requests.
3) Use retrieval only when message is underspecified.
