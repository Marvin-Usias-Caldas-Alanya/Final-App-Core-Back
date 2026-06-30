from fastapi import APIRouter, HTTPException

from app.core.supabase import get_supabase
from app.schemas.originacion import (
    BuroRequest,
    CondicionarRequest,
    PreEvaluacionRequest,
    PromoverRequest,
)
from app.services.buro_service import simular_buro
from app.services.creditos_service import cuota_francesa
from app.services.preevaluacion_service import pre_evaluar_solicitud
from app.services.solicitudes_service import rechazar_solicitud

router = APIRouter()


@router.post("/pre-evaluar")
async def pre_evaluar(body: PreEvaluacionRequest) -> dict:
    return pre_evaluar_solicitud(
        monto_solicitado=body.monto_solicitado,
        plazo_meses=body.plazo_meses,
        ingresos=body.ingresos,
        gastos=body.gastos,
        tipo_negocio=body.tipo_negocio,
        con_desgravamen=body.con_desgravamen,
        cuota_estimada=body.cuota_estimada,
    )


@router.post("/buro")
async def consultar_buro(body: BuroRequest) -> dict:
    try:
        return simular_buro(body.numero_documento.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/verificar-caso-1")
async def verificar_caso_1() -> dict:
    """Caso académico 1: S/ 1,000 · 12 meses · TEA 43.92% → cuota S/ 100.95."""
    cuota = cuota_francesa(1000, 12, 43.92)
    return {
        "monto": 1000,
        "plazo_meses": 12,
        "tea": 43.92,
        "cuota_calculada": cuota,
        "cuota_esperada": 100.95,
        "valido": abs(cuota - 100.95) <= 0.02,
    }


@router.post("/promover")
async def promover_solicitud(body: PromoverRequest) -> dict:
    supabase = get_supabase()
    response = (
        supabase.table("solicitudes_credito")
        .select("*")
        .eq("id", body.solicitud_id)
        .maybe_single()
        .execute()
    )
    solicitud = response.data
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    estado = (solicitud.get("estado") or "").lower()
    if estado in ("rechazado", "desembolsado"):
        raise HTTPException(status_code=400, detail=f"Estado no válido: {estado}")

    if not body.firma_registrada:
        raise HTTPException(status_code=400, detail="Debe registrar firma del cliente")

    payload: dict = {
        "estado": "recibido_comite",
        "fecha_visita": solicitud.get("fecha_visita") or None,
    }
    if body.latitud is not None and body.longitud is not None:
        payload["latitud_visita"] = body.latitud
        payload["longitud_visita"] = body.longitud
    if body.observaciones:
        payload["observaciones_asesor"] = body.observaciones

    updated = (
        supabase.table("solicitudes_credito")
        .update(payload)
        .eq("id", body.solicitud_id)
        .select("*")
        .single()
        .execute()
    )

    try:
        supabase.table("sync_outbox").insert(
            {
                "entidad": "solicitudes_credito",
                "entidad_id": body.solicitud_id,
                "accion": "promover_comite",
                "payload": {"estado": "recibido_comite"},
                "estado_sync": "pendiente",
            }
        ).execute()
    except Exception:
        pass

    return {
        "message": "Solicitud promovida a comité",
        "solicitud": updated.data,
    }


@router.post("/{solicitud_id}/condicionar")
async def condicionar_solicitud(solicitud_id: str, body: CondicionarRequest) -> dict:
    supabase = get_supabase()
    updated = (
        supabase.table("solicitudes_credito")
        .update(
            {
                "estado": "condicionado",
                "monto_aprobado": body.monto_aprobado,
                "motivo_condicion": body.motivo or "Condicionado por pre-evaluación/buró",
            }
        )
        .eq("id", solicitud_id)
        .select("*")
        .single()
        .execute()
    )
    return {"message": "Solicitud condicionada", "solicitud": updated.data}


@router.post("/{solicitud_id}/rechazar-originacion")
async def rechazar_originacion(solicitud_id: str, motivo: str = "Rechazado en originación") -> dict:
    supabase = get_supabase()
    solicitud = rechazar_solicitud(supabase, solicitud_id, motivo=motivo)
    return {"message": "Solicitud rechazada", "solicitud": solicitud}
