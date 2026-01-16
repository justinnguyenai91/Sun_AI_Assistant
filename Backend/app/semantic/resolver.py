def resolve(self, semantic_request: dict) -> dict:
    return {
        "source": semantic_request["dataset"],
        "fields": semantic_request["fields"],
        "filters": semantic_request.get("filters", [])
    }
