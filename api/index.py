"""
Vercel serverless entrypoint — exposes the FastAPI ASGI app.

If the app fails to import (missing dependency, bad env var format, etc.), serve a
minimal ASGI app that reports the error as JSON instead of an opaque
FUNCTION_INVOCATION_FAILED, so the cause is visible without digging through logs.
"""
import json
import traceback

try:
    from app.main import app  # noqa: F401
except Exception as exc:  # pragma: no cover - only hit on broken deployments
    _error = {
        "success": False,
        "error_code": "STARTUP_FAILED",
        "detail": f"{type(exc).__name__}: {exc}",
        "trace": traceback.format_exc().splitlines()[-6:],
    }
    print("PayLedger startup failed:\n" + traceback.format_exc(), flush=True)

    async def app(scope, receive, send):  # type: ignore[no-redef]
        if scope["type"] != "http":
            return
        body = json.dumps(_error).encode()
        await send({
            "type": "http.response.start",
            "status": 503,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({"type": "http.response.body", "body": body})
