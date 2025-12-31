import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from .settings import settings

limiter = Limiter(key_func=get_remote_address)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.time()
        response: Response = await call_next(request)
        dur = int((time.time()-start)*1000)
        response.headers["x-request-id"] = rid
        # access log gọn
        # (Bài 3 sẽ ghi DB; ở đây chỉ in console)
        print(f"[ACCESS] rid={rid} {request.method} {request.url.path} {response.status_code} {dur}ms")
        return response
