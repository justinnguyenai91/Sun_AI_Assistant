from data_engine.loaders.csv_loader import CSVLoader
from data_engine.loaders.postgres_loader import PostgresLoader
from data_engine.operators.groupby import group_and_aggregate

class DataEngine:
    def __init__(self, datasource="csv"):
        self.datasource = datasource

        if datasource == "csv":
            self.loader = CSVLoader()
        elif datasource == "postgres":
            self.loader = PostgresLoader()
        else:
            raise ValueError("Unsupported datasource")

    def execute(self, decision):
        df = self.loader.load(decision.table)

        # aggregate
        if decision.group_by and decision.metrics:
            agg_map = {
                m.field: m.agg
                for m in decision.metrics
            }
            df = df.groupby(decision.group_by).agg(agg_map).reset_index()

        # order by
        if decision.order_by:
            df = df.sort_values(
                by=decision.order_by.field,
                ascending=decision.order_by.direction == "asc"
            )

        # limit
        if decision.limit:
            df = df.head(decision.limit)

        return df.to_dict(orient="records")
