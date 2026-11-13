"""Application configuration using environment variables."""

import os
from typing import List


APP_NAME: str = os.getenv("APP_NAME", "MARS-X")
VERSION: str = os.getenv("VERSION", "0.1.0")
API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")

# CORS — comma-separated origins in the env var, default to localhost:3000
_cors_raw: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
CORS_ORIGINS: List[str] = [o.strip() for o in _cors_raw.split(",") if o.strip()]
