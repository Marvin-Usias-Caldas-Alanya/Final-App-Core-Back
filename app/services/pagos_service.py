import logging
from typing import Any

from fastapi import HTTPException
from supabase import Client

from app.services.solicitudes_service import datetime_now_iso, now_timestamp_ms

logger = logging.getLogger(__name__)


def pagar_cuota_demo(supabase: Client, credito_id: str) -> dict[str, Any]:
    credito_resp = (
        supabase.table("creditos")
        .select("*")
        .eq("id", credito_id)
        .maybe_single()
        .execute()
    )
    credito = credito_resp.data
    if not credito:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")

    cuota_resp = (
        supabase.table("cronograma_credito")
        .select("*")
        .eq("credito_id", credito_id)
        .neq("estado", "pagado")
        .order("numero_cuota")
        .limit(1)
        .execute()
    )
    cuotas = cuota_resp.data or []
    if not cuotas:
        return {"message": "No hay cuotas pendientes"}

    cuota_pendiente = cuotas[0]
    monto_cuota = float(cuota_pendiente.get("cuota") or 0)
    capital = float(cuota_pendiente.get("capital") or 0)
    fecha_pago = datetime_now_iso()

    supabase.table("cronograma_credito").update(
        {
            "estado": "pagado",
            "monto_pagado": monto_cuota,
            "fecha_pago": fecha_pago,
        }
    ).eq("id", cuota_pendiente["id"]).execute()

    saldo_actual = float(credito.get("saldo_actual") or 0)
    nuevo_saldo = max(saldo_actual - capital, 0)
    cuotas_pagadas = int(credito.get("cuotas_pagadas") or 0) + 1
    cuotas_total = int(credito.get("cuotas_total") or 0)

    credito_update: dict[str, Any] = {
        "cuotas_pagadas": cuotas_pagadas,
        "saldo_actual": nuevo_saldo,
    }
    if cuotas_pagadas >= cuotas_total > 0:
        credito_update["estado"] = "pagado"

    supabase.table("creditos").update(credito_update).eq("id", credito_id).execute()

    referencia = f"PAGO-DEMO-{now_timestamp_ms()}"
    movimiento_payload = {
        "cliente_id": credito.get("cliente_id"),
        "credito_id": credito_id,
        "tipo": "pago_credito",
        "descripcion": "Pago de cuota demo",
        "monto": monto_cuota,
        "moneda": "PEN",
        "fecha_movimiento": fecha_pago,
        "saldo_resultante": nuevo_saldo,
        "referencia": referencia,
    }
    movimiento_insert = (
        supabase.table("movimientos")
        .insert(movimiento_payload)
        .select("*")
        .single()
        .execute()
    )

    cuota_actualizada = (
        supabase.table("cronograma_credito")
        .select("*")
        .eq("id", cuota_pendiente["id"])
        .single()
        .execute()
    ).data

    credito_actualizado = (
        supabase.table("creditos")
        .select("*")
        .eq("id", credito_id)
        .single()
        .execute()
    ).data

    logger.info(
        "Pago demo registrado: credito=%s cuota=%s",
        credito_id,
        cuota_pendiente.get("numero_cuota"),
    )

    return {
        "message": "Pago registrado correctamente",
        "cuota": cuota_actualizada,
        "movimiento": movimiento_insert.data,
        "credito": credito_actualizado,
    }
