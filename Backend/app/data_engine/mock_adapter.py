from typing import Dict, Any, List
import asyncio


class MockDataAdapter:
    """
    Simple async mock adapter that returns sample MES-like data.
    This avoids touching CSV-related code and lets you test API flow.
    """

    async def execute(self, execution_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        await asyncio.sleep(0)  # keep async
        action = execution_plan.get("action")
        if action == "get_mes_report":
            target = execution_plan.get("target")
            # return a small mock dataset grouped by line with monthly samples
            return [
                {"line": "L1", "month": "2024-01", "quantity": 1200},
                {"line": "L1", "month": "2024-02", "quantity": 1100},
                {"line": "L2", "month": "2024-01", "quantity": 900},
                {"line": "L2", "month": "2024-02", "quantity": 950},
            ]
        return []
