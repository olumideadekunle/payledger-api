"""Root entrypoint for Vercel's FastAPI zero-config preset (delegates to api/index.py)."""
from api.index import app  # noqa: F401
