import os, time, json, requests
from typing import List, Dict, Any

class SunAI:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: int = 120):
        self.base = base_url.rstrip("/")
        self.key  = api_key or os.getenv("SUN_API_KEY")
        self.timeout = timeout

    def _headers(self): 
        return {"Authorization": f"Bearer {self.key}", "Content-Type":"application/json"}

    def chat(self, model: str, messages: List[Dict[str, Any]], **opts) -> Dict[str, Any]:
        body = {"model": model, "messages": messages} | opts
        # retry đơn giản
        for i in range(3):
            try:
                r = requests.post(f"{self.base}/v1/chat/completions",
                                  headers=self._headers(),
                                  data=json.dumps(body),
                                  timeout=self.timeout)
                if r.status_code == 429 and i < 2:
                    time.sleep(1.5*(i+1)); 
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                if i == 2: raise
                time.sleep(1.0*(i+1))
