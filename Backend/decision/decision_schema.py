# from typing import List, Optional, Dict, Any
# from pydantic import BaseModel

# class Decision(BaseModel):
#     datasource: str                 # csv | postgres
#     table: str                      # logical table name
#     metrics: List[str]              # ["revenue"]
#     group_by: Optional[List[str]] = None
#     filters: Optional[Dict[str, Any]] = None
#     order_by: Optional[str] = None  # revenue_desc
#     limit: Optional[int] = None
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class Metric(BaseModel):
    field: str        # revenue
    agg: str          # sum | avg | count | max | min

class OrderBy(BaseModel):
    field: str        # column name to sort by
    direction: str    # asc | desc

class Decision(BaseModel):
    datasource: str                 # csv | postgres
    table: str                      # logical table name
    metrics: List[Metric]           # [{"field": "revenue", "agg": "sum"}]
    group_by: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    order_by: Optional[OrderBy] = None  # {'field': 'revenue', 'direction': 'desc'}
    limit: Optional[int] = None
