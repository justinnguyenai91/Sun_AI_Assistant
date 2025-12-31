from fastapi import Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings

def attach_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["POST","GET","OPTIONS"],
        allow_headers=["*"],
    )

def require_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    key = authorization.split(" ",1)[1]
    if key not in settings.API_KEYS:
        raise HTTPException(403, "Invalid API key")
    return key
