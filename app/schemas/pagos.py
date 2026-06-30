from typing import Any

from pydantic import BaseModel


class PagoCuotaResponse(BaseModel):
    message: str
    cuota: dict[str, Any] | None = None
    movimiento: dict[str, Any] | None = None
    credito: dict[str, Any] | None = None


class MensajeResponse(BaseModel):
    message: str
