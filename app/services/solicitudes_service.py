import logging
from typing import Any

from fastapi import HTTPException
from supabase import Client

logger = logging.getLogger(__name__)


def _fetch_solicitud(supabase: Client, solicitud_id: str) -> dict[str, Any]:
    response = (
        supabase.table("solicitudes_credito")
        .select("*")
        .eq("id", solicitud_id)
        .maybe_single()
        .execute()
    )
    solicitud = response.data
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud


def aprobar_solicitud(supabase: Client, solicitud_id: str) -> dict[str, Any]:
    solicitud = _fetch_solicitud(supabase, solicitud_id)
    estado = (solicitud.get("estado") or "").lower()

    if estado == "desembolsado":
        raise HTTPException(
            status_code=400,
            detail="La solicitud ya fue desembolsada",
        )

    monto_solicitado = solicitud.get("monto_solicitado") or 0

    updated = (
        supabase.table("solicitudes_credito")
        .update(
            {
                "estado": "aprobado",
                "monto_aprobado": monto_solicitado,
            }
        )
        .eq("id", solicitud_id)
        .select("*")
        .single()
        .execute()
    )

    logger.info("Solicitud %s aprobada", solicitud_id)
    return updated.data


def rechazar_solicitud(
    supabase: Client,
    solicitud_id: str,
    motivo: str = "Rechazado desde Core Web",
) -> dict[str, Any]:
    solicitud = _fetch_solicitud(supabase, solicitud_id)
    estado = (solicitud.get("estado") or "").lower()

    if estado == "desembolsado":
        raise HTTPException(
            status_code=400,
            detail="No se puede rechazar una solicitud desembolsada",
        )

    updated = (
        supabase.table("solicitudes_credito")
        .update(
            {
                "estado": "rechazado",
                "motivo_rechazo": motivo,
            }
        )
        .eq("id", solicitud_id)
        .select("*")
        .single()
        .execute()
    )

    logger.info("Solicitud %s rechazada", solicitud_id)
    return updated.data


def desembolsar_solicitud(
    supabase: Client,
    solicitud_id: str,
    *,
    notificacion_mensaje: str | None = None,
) -> dict[str, Any]:
    from app.services.creditos_service import (
        DEFAULT_TEA,
        PRODUCTO_NOMBRE,
        generar_cronograma,
    )

    solicitud = _fetch_solicitud(supabase, solicitud_id)
    estado = (solicitud.get("estado") or "").lower()

    if estado == "desembolsado":
        raise HTTPException(
            status_code=400,
            detail="La solicitud ya está desembolsada",
        )

    cliente_id = solicitud.get("cliente_id")
    asesor_id = solicitud.get("asesor_id")
    agencia_id = solicitud.get("agencia_id")
    monto = float(solicitud.get("monto_aprobado") or solicitud.get("monto_solicitado") or 0)
    plazo_meses = int(solicitud.get("plazo_meses") or 0)
    tea = float(solicitud.get("tea_referencial") or DEFAULT_TEA)

    if not cliente_id:
        raise HTTPException(status_code=400, detail="La solicitud no tiene cliente_id")
    if monto <= 0 or plazo_meses <= 0:
        raise HTTPException(status_code=400, detail="Monto o plazo inválido en la solicitud")

    now = datetime_now_iso()
    fecha_hoy = now[:10]
    fecha_vencimiento = add_months_iso(fecha_hoy, plazo_meses)

    credito_payload = {
        "cliente_id": cliente_id,
        "asesor_id": asesor_id,
        "agencia_id": agencia_id,
        "producto": PRODUCTO_NOMBRE,
        "monto_desembolsado": monto,
        "plazo_meses": plazo_meses,
        "tea": tea,
        "estado": "vigente",
        "fecha_desembolso": fecha_hoy,
        "fecha_vencimiento": fecha_vencimiento,
        "saldo_actual": monto,
        "cuotas_total": plazo_meses,
        "cuotas_pagadas": 0,
        "dias_mora": 0,
    }

    credito_insert = (
        supabase.table("creditos")
        .insert(credito_payload)
        .select("*")
        .single()
        .execute()
    )
    credito = credito_insert.data
    credito_id = str(credito["id"])

    cronograma = generar_cronograma(
        credito_id=credito_id,
        monto=monto,
        plazo_meses=plazo_meses,
        tea_percent=tea,
    )

    if cronograma:
        supabase.table("cronograma_credito").insert(cronograma).execute()

    referencia = f"DESEMBOLSO-{int(now_timestamp_ms())}"
    movimiento_payload = {
        "cliente_id": cliente_id,
        "credito_id": credito_id,
        "tipo": "desembolso",
        "descripcion": "Desembolso de crédito",
        "monto": monto,
        "moneda": "PEN",
        "fecha_movimiento": now,
        "saldo_resultante": monto,
        "referencia": referencia,
    }
    supabase.table("movimientos").insert(movimiento_payload).execute()

    supabase.table("solicitudes_credito").update({"estado": "desembolsado"}).eq(
        "id", solicitud_id
    ).execute()

    _try_create_notificacion(
        supabase,
        cliente_id=cliente_id,
        titulo="Crédito desembolsado",
        mensaje=notificacion_mensaje
        or f"Se desembolsó S/ {monto:.2f} en {PRODUCTO_NOMBRE}.",
    )

    logger.info(
        "Desembolso completado: solicitud=%s credito=%s cuotas=%s",
        solicitud_id,
        credito_id,
        len(cronograma),
    )

    return {
        "message": "Crédito desembolsado",
        "credito": credito,
        "cronograma_count": len(cronograma),
    }


def datetime_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def now_timestamp_ms() -> int:
    from datetime import UTC, datetime

    return int(datetime.now(UTC).timestamp() * 1000)


def add_months_iso(fecha_iso: str, meses: int) -> str:
    from datetime import date

    from dateutil.relativedelta import relativedelta

    base = date.fromisoformat(fecha_iso)
    return (base + relativedelta(months=meses)).isoformat()


def _try_create_notificacion(
    supabase: Client,
    *,
    cliente_id: Any,
    titulo: str,
    mensaje: str,
) -> None:
    try:
        supabase.table("notificaciones").insert(
            {
                "cliente_id": cliente_id,
                "titulo": titulo,
                "mensaje": mensaje,
                "leida": False,
            }
        ).execute()
    except Exception as exc:
        logger.warning("No se pudo crear notificación (tabla opcional): %s", exc)
