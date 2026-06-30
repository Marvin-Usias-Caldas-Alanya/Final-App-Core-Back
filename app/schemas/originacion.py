from pydantic import BaseModel, Field


class PreEvaluacionRequest(BaseModel):
    monto_solicitado: float = Field(gt=0)
    plazo_meses: int = Field(ge=1, le=360)
    ingresos: float = Field(ge=0)
    gastos: float = Field(ge=0)
    tipo_negocio: str | None = None
    con_desgravamen: bool = False
    cuota_estimada: float | None = None


class BuroRequest(BaseModel):
    numero_documento: str = Field(min_length=8, max_length=12)


class PromoverRequest(BaseModel):
    solicitud_id: str
    latitud: float | None = None
    longitud: float | None = None
    firma_registrada: bool = False
    observaciones: str | None = None


class CondicionarRequest(BaseModel):
    monto_aprobado: float = Field(gt=0)
    motivo: str | None = None
