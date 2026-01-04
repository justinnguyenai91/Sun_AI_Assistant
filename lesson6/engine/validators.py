ALLOWED_AGG = {"sum", "avg", "min", "max", "count", None}

def validate_instruction(instr: dict, columns: list):
    for col in instr.get("metrics", []):
        if col not in columns:
            raise ValueError(f"Column not found: {col}")

    if instr["aggregation"] not in ALLOWED_AGG:
        raise ValueError("Unsupported aggregation")

    for f in instr.get("filters", []):
        if f["column"] not in columns:
            raise ValueError(f"Filter column not found: {f['column']}")
