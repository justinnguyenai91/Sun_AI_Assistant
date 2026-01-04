def execute_csv(df, instr):
    data = df

    for f in instr.get("filters", []):
        op = f["operator"]
        if op == "=":
            data = data[data[f["column"]] == f["value"]]
        elif op == ">":
            data = data[data[f["column"]] > f["value"]]

    if instr["aggregation"]:
        data = data.groupby(instr["group_by"])[instr["metrics"][0]]
        agg_map = {
            "sum": data.sum,
            "avg": data.mean,
            "min": data.min,
            "max": data.max,
            "count": data.count
        }
        data = agg_map[instr["aggregation"]]().reset_index()

    if "order_by" in instr:
        data = data.sort_values(
            instr["order_by"]["column"],
            ascending=instr["order_by"]["direction"] == "asc"
        )

    if "limit" in instr:
        data = data.head(instr["limit"])

    return data
def execute_postgres(conn, table, instr):
    cols = instr["metrics"] + instr.get("group_by", [])
    select_cols = ", ".join(cols)

    sql = f"SELECT {select_cols} FROM {table}"
    params = []

    if instr.get("filters"):
        where = []
        for f in instr["filters"]:
            where.append(f"{f['column']} {f['operator']} %s")
            params.append(f["value"])
        sql += " WHERE " + " AND ".join(where)

    # aggregation & group by
    if instr["aggregation"]:
        sql = sql.replace(
            instr["metrics"][0],
            f"{instr['aggregation'].upper()}({instr['metrics'][0]})"
        )
        sql += f" GROUP BY {', '.join(instr['group_by'])}"

    if "order_by" in instr:
        sql += f" ORDER BY {instr['order_by']['column']} {instr['order_by']['direction'].upper()}"

    if "limit" in instr:
        sql += " LIMIT %s"
        params.append(instr["limit"])

    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()
