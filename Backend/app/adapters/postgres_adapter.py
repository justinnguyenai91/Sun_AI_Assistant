import asyncpg
from typing import Any, Dict, List, Tuple, Optional


class PostgresAdapter:
    """
    PostgreSQL data adapter.
    - No business logic
    - No KPI / metric awareness
    - SQL built strictly from execution plan + semantic config
    """

    def __init__(
        self,
        dsn: str,
        semantic_config: Dict[str, Any],
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ):
        self.dsn = dsn
        self.semantic_config = semantic_config
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self._pool: Optional[asyncpg.Pool] = None

    async def init(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=30,
            )

    async def execute(self, execution_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self._pool is None:
            raise RuntimeError("PostgresAdapter not initialized")

        sql, params = self._build_sql(execution_plan)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_sql(self, plan: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        Build SQL strictly from execution plan + semantic config.
        No hardcoded SQL.
        """

        datasource = plan["datasource"]
        entity = plan["entity"]

        ds_cfg = self.semantic_config["datasources"][datasource]
        entity_cfg = ds_cfg["schema_mapping"][entity]

        table = entity_cfg["table"]
        column_map = entity_cfg["columns"]

        # SELECT
        select_fields = plan.get("select")
        if not select_fields:
            raise ValueError("Execution plan must define select fields")

        select_clause = ", ".join(
            f"{table}.{column_map[f]} AS {f}" for f in select_fields
        )

        sql = f"SELECT {select_clause} FROM {table}"
        params: List[Any] = []

        # WHERE
        filters = plan.get("filters", [])
        if filters:
            conditions = []
            for f in filters:
                col = column_map[f["field"]]
                op = f["op"]
                conditions.append(f"{table}.{col} {op} ${len(params) + 1}")
                params.append(f["value"])
            sql += " WHERE " + " AND ".join(conditions)

        # GROUP BY
        group_by = plan.get("group_by", [])
        if group_by:
            gb_clause = ", ".join(f"{table}.{column_map[g]}" for g in group_by)
            sql += f" GROUP BY {gb_clause}"

        # LIMIT
        if "limit" in plan:
            sql += f" LIMIT {int(plan['limit'])}"

        return sql, params
