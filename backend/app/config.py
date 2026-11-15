"""Application configuration using environment variables."""

import os
from typing import List


APP_NAME: str = os.getenv("APP_NAME", "MARS-X")
VERSION: str = os.getenv("VERSION", "0.1.0")
API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
HOST: str = os.getenv("HOST", "0.0.0.0" if os.getenv("PORT") else "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8000"))


# Production and local development CORS origins
DEFAULT_CORS_ORIGINS: List[str] = [
    # Production Vercel frontend (Requirement 1)
    "https://mars-x-nasa.vercel.app",
    # Production Render backend & cloud deployments
    "https://mars-x-backend.onrender.com",
    "https://mars-x-cc6e.onrender.com",
    # Local development origins (Requirement 2)
    "http://localhost:3005",
    "http://127.0.0.1:3005",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
]

# Allow runtime customization via CORS_ORIGINS environment variable
# Strict rule: Never inject wildcard '*' when credentials are enabled (Requirement 5)
_cors_raw: str = os.getenv("CORS_ORIGINS", "")
if _cors_raw:
    _custom_origins = [o.strip().rstrip("/") for o in _cors_raw.split(",") if o.strip()]
    CORS_ORIGINS: List[str] = [
        o for o in dict.fromkeys(DEFAULT_CORS_ORIGINS + _custom_origins) if o != "*"
    ]
else:
    CORS_ORIGINS: List[str] = [o for o in DEFAULT_CORS_ORIGINS if o != "*"]

# Absolute path to datasets root directory
DEFAULT_DATA_DIR: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'data')
)
DATA_ROOT: str = os.getenv('MARS_DATA_DIR', os.getenv('DATA_ROOT', DEFAULT_DATA_DIR))
