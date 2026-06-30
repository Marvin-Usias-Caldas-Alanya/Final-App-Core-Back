"""Autenticación JWT para apps móviles (RBAC básico)."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.security import create_access_token

router = APIRouter()

_DEMO_USERS: dict[str, dict[str, str]] = {
    "asesor": {"password": "123456", "role": "asesor", "subject": "asesor-demo"},
    "supervisor": {"password": "123456", "role": "supervisor", "subject": "supervisor-demo"},
    "admin": {"password": "123456", "role": "admin", "subject": "admin-demo"},
    "cliente": {"password": "123456", "role": "cliente", "subject": "cliente-demo"},
}


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    tipo: str = Field(default="asesor", description="asesor|cliente|supervisor|admin")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in_minutes: int = 60


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    user = _DEMO_USERS.get(body.tipo.lower())
    if user is None:
        raise HTTPException(status_code=400, detail="Tipo de usuario no válido")

    if body.password != user["password"]:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_access_token(
        user["subject"],
        expires_delta=timedelta(minutes=60),
        extra_claims={"role": user["role"], "username": body.username},
    )
    return TokenResponse(access_token=token, role=user["role"])
