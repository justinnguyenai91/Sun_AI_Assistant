from fastapi import FastAPI

# Keep the original entrypoint but import and mount routes
# from the gateway app implementation to ensure a single served app
from app.config import (
    EXTERNAL_API_BASE_URL,
    EXTERNAL_API_PREFIX,
    EXTERNAL_API_TOKEN,
)

from app.app import app as gateway_app  # import FastAPI instance from app/app.py

# Expose the gateway app as the module-level `app` for uvicorn
app = gateway_app
