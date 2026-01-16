from typing import List, Dict, Any
from pydantic import BaseModel, Field


class MetricDefinition(BaseModel):
    name: str
    description: str | None = None
    unit: str | None = None
    formula: str | None = None  # symbolic only


class RuleCondition(BaseModel):
    operator: str               # <, <=, >, >=, ==
    value_from: str             # path in config/context


class RuleDefinition(BaseModel):
    id: str
    applies_to: str             # metric name
    conditions: List[RuleCondition]
    decision: str               # OK / WARNING / CRITICAL
    reason: str                 # message template


class SemanticConfig(BaseModel):
    metrics: Dict[str, MetricDefinition]
    rules: List[RuleDefinition]
