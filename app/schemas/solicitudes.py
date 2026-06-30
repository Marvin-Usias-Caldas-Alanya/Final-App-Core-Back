from typing import Any

from pydantic import BaseModel


class SolicitudResponse(BaseModel):
    solicitud: dict[str, Any]


class DesembolsoResponse(BaseModel):
    message: str
    credito: dict[str, Any]
    cronograma_count: int
