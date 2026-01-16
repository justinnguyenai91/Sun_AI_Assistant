import yaml
from pathlib import Path
from .schema import SemanticConfig


class SemanticConfigLoader:
    """
    LOAD + VALIDATE semantic YAML
    DO NOT put any business logic here
    """

    def __init__(self, semantic_dir: Path):
        self.semantic_dir = semantic_dir

    def load(self) -> SemanticConfig:
        with open(self.semantic_dir / "metrics.yaml", "r", encoding="utf-8") as f:
            metrics_data = yaml.safe_load(f)

        with open(self.semantic_dir / "rules.yaml", "r", encoding="utf-8") as f:
            rules_data = yaml.safe_load(f)

        payload = {
            "metrics": metrics_data.get("metrics", {}),
            "rules": rules_data.get("rules", []),
        }

        return SemanticConfig.model_validate(payload)
