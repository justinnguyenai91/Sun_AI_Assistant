# SemanticRequest Spec (v1)

Goal: a **stable internal contract** for turning natural-language chat into config-driven KPI queries.

This object is produced by:
- rule parser (fast, deterministic)
- optional LLM parser (slot-filling)
- session resolver (defaults + continuity)

…and consumed by:
- Planner (ontology + templates)
- Event log (audit + replay)
- Future vector memory (embedding / retrieval)

## 1) SemanticRequest (canonical)

### 1.1 Minimal example

```json
{
  "version": "1.0",
  "intent": "report",
  "entity": "production",
  "time": {
    "mode": "iso_last_week",
    "from": "2026-01-05",
    "to": "2026-01-11",
    "tz_offset_hours": 7
  },
  "group_by": ["date", "line"],
  "metrics": ["plan_qty", "actual_production_qty", "achievement_rate"],
  "filters": {},
  "context": {
    "user_id": "u_123",
    "session_id": "s_abc",
    "locale": "vi",
    "factoryCodes": ["DJVN1"]
  },
  "assumptions": [
    "Resolved 'last week' as ISO week Mon–Sun",
    "Defaulted group_by to ['date','line'] for current_production"
  ],
  "clarifications": []
}
```

### 1.2 Field definitions

- `version` (string): semantic contract version, e.g. `"1.0"`.

- `intent` (enum):
  - `report`: retrieve/compute KPIs and return table/chart
  - `explain`: explain terms / definitions (chat-only)
  - `ui`: UI-only commands (hide column, change sorting, etc.)

- `entity` (enum-ish string): e.g. `production`, `defect`. Keep aligned with ontology entities.

- `time` (object):
  - `mode` (enum):
    - `absolute_range`: explicit `from/to`
    - `iso_last_week`: ISO week Mon–Sun immediately before current ISO week
    - `iso_this_week`: ISO week Mon–Sun for current ISO week
    - `yesterday`, `today`, `last_n_days`
  - `from` (YYYY-MM-DD)
  - `to` (YYYY-MM-DD)
  - `tz_offset_hours` (int): used when timestamps are UTC but grouping is local

- `group_by` (array of dimension ids): order matters.
  - Examples: `["date","line"]`, `["date","shift"]`, `["month","line"]`

- `metrics` (array of metric ids): these must be ontology keys.
  - Example for "current production": `plan_qty`, `actual_production_qty`, `achievement_rate`

- `filters` (object): stable filter slots; planner maps into templates.
  - Examples: `shift`, `processType`, `finalYn`, `reflect`, `lineCodes`, `modelCodes`

- `context` (object): session/user routing and UI context.
  - `user_id`, `session_id`, `locale`
  - `factoryCode` (string) OR `factoryCodes` (array)
  - `debug` (bool)

- `assumptions` (array of strings): human-readable explanations.

- `clarifications` (array of objects): follow-up questions when required.
  - Example:
    ```json
    {"type":"missing_factory","prompt":"Which factory?","options":["FAC01","DJVN1"]}
    ```

## 2) JSON Schema (Draft)

This is for validation/logging; it doesn’t need to be perfect for v1.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["version", "intent", "context"],
  "properties": {
    "version": {"type": "string"},
    "intent": {"type": "string", "enum": ["report", "explain", "ui"]},
    "entity": {"type": "string"},
    "time": {
      "type": "object",
      "properties": {
        "mode": {"type": "string"},
        "from": {"type": "string"},
        "to": {"type": "string"},
        "tz_offset_hours": {"type": "integer"}
      }
    },
    "group_by": {"type": "array", "items": {"type": "string"}},
    "metrics": {"type": "array", "items": {"type": "string"}},
    "filters": {"type": "object"},
    "context": {
      "type": "object",
      "required": ["session_id"],
      "properties": {
        "user_id": {"type": "string"},
        "session_id": {"type": "string"},
        "locale": {"type": "string"},
        "factoryCode": {"type": "string"},
        "factoryCodes": {"type": "array", "items": {"type": "string"}},
        "debug": {"type": "boolean"}
      }
    },
    "assumptions": {"type": "array", "items": {"type": "string"}},
    "clarifications": {"type": "array", "items": {"type": "object"}}
  }
}
```

## 3) Resolution rules (v1)

### 3.1 ISO week definition (confirmed)
- ISO week starts **Monday** and ends **Sunday**.
- `iso_last_week` refers to the previous ISO week relative to "now" in local timezone.

### 3.2 Default meaning for “current production” (confirmed)
Per-user default KPI bundle `current_production`:
- metrics: `plan_qty`, `actual_production_qty`, `achievement_rate`
- group_by: `["date","line"]`

### 3.3 Factory requirement
For data requests:
- If `factoryCodes` missing, use session state.
- If still missing: create `clarifications=[{type:"missing_factory",...}]`.

### 3.4 Continuity behavior
If the new message omits dimensions/filters:
- inherit from session state if the user’s intent is compatible
- otherwise fallback to user defaults (bundle)

Compatibility example:
- If last query was production report → next "last week" production query can inherit `factoryCodes` and group_by.
- If switching entity (defect → production), do not inherit metrics blindly.
