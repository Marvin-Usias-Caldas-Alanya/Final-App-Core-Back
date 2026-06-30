from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(BASE_DIR / ".env", override=True)

import os  # noqa: E402


def _read_env() -> None:
    load_dotenv(BASE_DIR / ".env", override=True)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    value = value.strip()
    return value or None


SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_ANON_KEY = _env("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = _env("SUPABASE_SERVICE_ROLE_KEY")
API_ENV = _env("API_ENV", "dev") or "dev"
JWT_SECRET = _env("JWT_SECRET", "") or ""
SESSION_SECRET = _env("SESSION_SECRET", JWT_SECRET or "core-mobile-demo-secret") or "core-mobile-demo-secret"
WEB_ADMIN_USER = _env("WEB_ADMIN_USER", "admin") or "admin"
WEB_ADMIN_PASSWORD = _env("WEB_ADMIN_PASSWORD", "admin123") or "admin123"


def refresh_env() -> None:
    global SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, API_ENV

    _read_env()
    SUPABASE_URL = _env("SUPABASE_URL")
    SUPABASE_ANON_KEY = _env("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY = _env("SUPABASE_SERVICE_ROLE_KEY")
    API_ENV = _env("API_ENV", "dev") or "dev"


def supabase_configured() -> bool:
    refresh_env()
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def health_payload() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "core_mobile_api",
        "supabase": "configured" if supabase_configured() else "missing",
    }


def debug_env_payload() -> dict[str, str | bool]:
    refresh_env()
    key = SUPABASE_SERVICE_ROLE_KEY or ""
    return {
        "env_path": str(ENV_PATH),
        "env_exists": ENV_PATH.exists(),
        "supabase_url_loaded": bool(SUPABASE_URL),
        "service_role_loaded": bool(SUPABASE_SERVICE_ROLE_KEY),
        "service_role_prefix": key[:10] if key else "",
    }
