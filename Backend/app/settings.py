# # Backend/settings.py
# from pydantic import BaseModel
# from pathlib import Path
# from dotenv import load_dotenv
# import os

# class Settings(BaseModel):
#     load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

#     BACKEND: str = os.getenv("BACKEND", "llama")

#     LLAMA_URL: str = os.getenv("LLAMA_URL", "http://127.0.0.1:8080")
#     OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

#     # OpenAI-compatible path (llama.cpp, vLLM, Ollama đều dùng được)
#     CHAT_COMPLETION_PATH: str = os.getenv(
#         "CHAT_COMPLETION_PATH",
#         "/v1/chat/completions"
#     )

#     MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen2-7b")

#     API_KEYS: list[str] = [
#         k.strip() for k in os.getenv("API_KEYS", "dev-key-123").split(",") if k.strip()
#     ]
#     ADMIN_KEYS: list[str] = [
#         k.strip() for k in os.getenv("ADMIN_KEYS", "admin-key-xyz").split(",") if k.strip()
#     ]

#     RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "60"))
#     ALLOW_ORIGINS: list[str] = [
#         o.strip() for o in os.getenv("ALLOW_ORIGINS", "http://localhost:5173").split(",") if o.strip()
#     ]
#     PORT: int = int(os.getenv("PORT", "9000"))

# settings = Settings()

# Backend/settings.py

from pydantic import BaseModel, model_validator
from pathlib import Path
from dotenv import load_dotenv
import os

# ===============================
# Bootstrap: load .env once
# ===============================
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))


# ===============================
# Settings Schema
# ===============================
class Settings(BaseModel):
    # ---- Core backend switch ----
    BACKEND: str  # llama | ollama | openai (future)

    # ---- LLM endpoints ----
    LLAMA_URL: str | None = None
    OLLAMA_URL: str | None = None

    # ---- OpenAI-compatible contract ----
    CHAT_COMPLETION_PATH: str = "/v1/chat/completions"
    MODEL_NAME: str = "qwen2-7b"

    # ---- Security / Ops ----
    API_KEYS: list[str]
    ADMIN_KEYS: list[str] = []

    RATE_LIMIT: int
    ALLOW_ORIGINS: list[str]
    PORT: int

    # ===============================
    # Cross-field validation
    # ===============================
    @model_validator(mode="after")
    def validate_backend(self):
        if self.BACKEND == "llama" and not self.LLAMA_URL:
            raise ValueError("BACKEND=llama requires LLAMA_URL")

        if self.BACKEND == "ollama" and not self.OLLAMA_URL:
            raise ValueError("BACKEND=ollama requires OLLAMA_URL")

        return self


# ===============================
# Helpers
# ===============================
def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# ===============================
# Singleton settings instance
# ===============================
settings = Settings(
    BACKEND=_require("BACKEND"),

    LLAMA_URL=os.getenv("LLAMA_URL"),
    OLLAMA_URL=os.getenv("OLLAMA_URL"),

    CHAT_COMPLETION_PATH=os.getenv(
        "CHAT_COMPLETION_PATH",
        "/v1/chat/completions"
    ),
    MODEL_NAME=os.getenv("MODEL_NAME", "qwen2-7b"),

    API_KEYS=[k.strip() for k in _require("API_KEYS").split(",") if k.strip()],
    ADMIN_KEYS=[k.strip() for k in os.getenv("ADMIN_KEYS", "").split(",") if k.strip()],

    RATE_LIMIT=int(_require("RATE_LIMIT")),
    ALLOW_ORIGINS=[o.strip() for o in _require("ALLOW_ORIGINS").split(",") if o.strip()],
    PORT=int(_require("PORT")),
)
