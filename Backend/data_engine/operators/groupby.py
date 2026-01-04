def group_and_aggregate(df, group_by, metrics):
    agg = {m: "sum" for m in metrics}
    return df.groupby(group_by, as_index=False).agg(agg)
