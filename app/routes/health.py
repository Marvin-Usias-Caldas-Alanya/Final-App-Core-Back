from fastapi import APIRouter

from app.core.config import debug_env_payload, health_payload

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return health_payload()


@router.get("/debug-env")
async def debug_env() -> dict[str, str | bool]:
    return debug_env_payload()
