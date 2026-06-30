from fastapi import HTTPException
from supabase import Client, create_client

from app.core import config

_supabase_admin: Client | None = None
_client_key: tuple[str, str] | None = None


def _build_client() -> Client:
    config.refresh_env()
    url = config.SUPABASE_URL
    key = config.SUPABASE_SERVICE_ROLE_KEY
    if not url or not key:
        raise HTTPException(
            status_code=503,
            detail="Supabase no configurado. Revise SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.",
        )
    return create_client(url, key)


def get_supabase_admin() -> Client:
    global _supabase_admin, _client_key

    config.refresh_env()
    url = config.SUPABASE_URL or ""
    key = config.SUPABASE_SERVICE_ROLE_KEY or ""
    current_key = (url, key)

    if not url or not key:
        raise HTTPException(
            status_code=503,
            detail="Supabase no configurado. Revise SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.",
        )

    if _supabase_admin is None or _client_key != current_key:
        _supabase_admin = create_client(url, key)
        _client_key = current_key

    return _supabase_admin


def get_supabase() -> Client:
    return get_supabase_admin()


class _SupabaseAdminProxy:
    """Lazy proxy: supabase_admin = create_client(...) al primer uso."""

    def __getattr__(self, name: str):
        return getattr(get_supabase_admin(), name)

    def __bool__(self) -> bool:
        config.refresh_env()
        return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY)


supabase_admin = _SupabaseAdminProxy()
