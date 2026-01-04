import requests

PLANNER_API = "http://127.0.0.1:9000/planner"

def call_llm(system_prompt: str, user_question: str) -> str:
    resp = requests.post(
        PLANNER_API,
        json={"question": user_question},
        timeout=60
    )
    resp.raise_for_status()

    return resp.json()["decision"]
