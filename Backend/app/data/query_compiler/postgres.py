from typing import Dict, Any
from app.data.query_compiler.base import QueryCompiler


class PostgresQueryCompiler(QueryCompiler):
    def compile(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        VERY IMPORTANT:
        - SQL is generated ONLY here
        - Deterministic
        - No business meaning
        """

        source = plan["source"]
        fields = plan["fields"]
        filters = plan.get("filters", [])

        where_clauses = []
        params = {}

        for idx, f in enumerate(filters):
            key = f"p{idx}"
            where_clauses.append(f"{f['field']} {f['op']} %({key})s")
            params[key] = f["value"]

        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)

        sql = f"""
            SELECT {", ".join(fields)}
            FROM {source}
            {where_sql}
        """

        return {
            "sql": sql,
            "params": params
        }
