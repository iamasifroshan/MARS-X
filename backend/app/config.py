"""Application configuration using environment variables."""

import os
from typing import List


APP_NAME: str = os.getenv("APP_NAME", "MARS-X")
VERSION: str = os.getenv("VERSION", "0.1.0")
API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8000"))


# CORS — comma-separated origins in the env var
_cors_raw: str = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3005,http://127.0.0.1:3005,http://localhost:3001,http://127.0.0.1:3001,http://localhost:4000,http://127.0.0.1:4000",
)
CORS_ORIGINS: List[str] = [o.strip() for o in _cors_raw.split(",") if o.strip()]
