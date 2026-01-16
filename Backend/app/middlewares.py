import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        # Short-circuit OPTIONS preflight to avoid hitting auth/validation logic
        if request.method == "OPTIONS":
            # Minimal CORS response for preflight
            headers = {
                "access-control-allow-origin": request.headers.get("origin", "*"),
                "access-control-allow-methods": "GET,POST,OPTIONS",
                "access-control-allow-headers": request.headers.get("access-control-request-headers", "Authorization,Content-Type"),
            }
            response = Response(status_code=200, headers=headers)
            print(f"[ACCESS] rid={rid} {request.method} {request.url.path} {response.status_code} 0ms")
            return response
        start = time.time()
        response: Response = await call_next(request)
        dur = int((time.time()-start)*1000)
        response.headers["x-request-id"] = rid
        # access log gọn
        # (Bài 3 sẽ ghi DB; ở đây chỉ in console)
        print(f"[ACCESS] rid={rid} {request.method} {request.url.path} {response.status_code} {dur}ms")
        return response
