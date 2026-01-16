import json

def parse_ai_response(text: str) -> dict:
    try:
        decision = json.loads(text)
    except json.JSONDecodeError:
        return {
            "error": "Invalid AI response",
            "suggestion": "AI must return valid JSON"
        }

    if "error" in decision:
        return decision

    required_keys = ["source", "action", "metrics", "aggregation"]
    for k in required_keys:
        if k not in decision:
            return {
                "error": "Invalid instruction",
                "suggestion": f"Missing key: {k}"
            }

    return decision
