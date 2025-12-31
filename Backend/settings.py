from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
import os

class Settings(BaseModel):
    # NẠP .env NGAY KHI import settings.py
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
    BACKEND: str = os.getenv("BACKEND", "llama")
    LLAMA_URL: str = os.getenv("LLAMA_URL", "http://127.0.0.1:8080")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

    API_KEYS: list[str] = [k.strip() for k in os.getenv("API_KEYS","dev-key-123").split(",") if k.strip()]
    ADMIN_KEYS: list[str] = [k.strip() for k in os.getenv("ADMIN_KEYS","admin-key-xyz").split(",") if k.strip()]

    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT","60"))
    ALLOW_ORIGINS: list[str] = [o.strip() for o in os.getenv("ALLOW_ORIGINS","http://localhost:5173").split(",") if o.strip()]
    PORT: int = int(os.getenv("PORT","9000"))

settings = Settings()
