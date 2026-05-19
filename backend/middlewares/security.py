import re
import json
import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Comprehensive regex for common XSS patterns
# 1. <script> tags
# 2. javascript: pseudo-protocol
# 3. HTML event handlers (onmouseover, onerror, etc.)
# 4. <iframe>, <object>, <embed>, <applet> tags
XSS_PATTERN = re.compile(
    r"(<script.*?>.*?</script>)|"                     # <script> tags
    r"(javascript\s*:)|"                              # javascript: protocol
    r"(on\w+\s*=)|"                                   # Event handlers like onerror=, onclick=
    r"(<iframe.*?>)|(<object.*?>)|(<embed.*?>)|(<applet.*?>)|" # Dangerous tags
    r"(<img.*?src\s*=.*?javascript:)|"                # img src with javascript
    r"(style\s*=.*?expression\s*\()",                 # CSS expressions (IE)
    re.IGNORECASE | re.DOTALL
)

class XSSMiddleware(BaseHTTPMiddleware):
    """
    Middleware to detect and block XSS patterns in POST/PUT/PATCH request bodies.
    """
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            # Check content type to ensure it's JSON
            content_type = request.headers.get("Content-Type", "")
            if "application/json" in content_type:
                # We must read the body, but it's a stream, so we need to replace it
                # for the downstream handlers to be able to read it again.
                body = await request.body()
                
                try:
                    body_str = body.decode("utf-8")
                    if XSS_PATTERN.search(body_str):
                        logger.warning(f"XSS Attempt blocked from IP: {request.client.host} on path: {request.url.path}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Malicious content detected (XSS Protection)."
                        )
                except UnicodeDecodeError:
                    # If it's not valid UTF-8, it might be binary or something else
                    pass
                except HTTPException as e:
                    # Re-raise HTTP exceptions to be caught by FastAPI
                    return Response(
                        content=json.dumps({"detail": e.detail}),
                        status_code=e.status_code,
                        media_type="application/json"
                    )

                # Reconstruct the request with the body we read
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request._receive = receive

        response = await call_next(request)
        return response
",file_path: