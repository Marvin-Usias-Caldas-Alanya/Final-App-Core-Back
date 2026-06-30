"""Pre-evaluación de capacidad de pago para originación móvil."""

from __future__ import annotations

from typing import Any

from app.core.tarifario import TEA_CON_DESGRAVAMEN, TEA_SIN_DESGRAVAMEN, resolver_producto
from app.services.creditos_service import cuota_francesa


CAPACIDAD_PAGO_FACTOR = 0.35
REDUCCION_CONDICIONADO = 0.60


def pre_evaluar_solicitud(
    *,
    monto_solicitado: float,
    plazo_meses: int,
    ingresos: float,
    gastos: float,
    tipo_negocio: str | None = None,
    con_desgravamen: bool = False,
    cuota_estimada: float | None = None,
) -> dict[str, Any]:
    producto = resolver_producto(tipo_negocio=tipo_negocio)
    tea = TEA_CON_DESGRAVAMEN if con_desgravamen else TEA_SIN_DESGRAVAMEN
    cuota = cuota_estimada or cuota_francesa(monto_solicitado, plazo_meses, tea)

    ingreso_disponible = max(0.0, ingresos - gastos)
    cuota_maxima = ingreso_disponible * CAPACIDAD_PAGO_FACTOR

    resultado: dict[str, Any] = {
        "producto": producto.codigo,
        "tea_aplicada": tea,
        "cuota_estimada": round(cuota, 2),
        "ingreso_disponible": round(ingreso_disponible, 2),
        "cuota_maxima_permitida": round(cuota_maxima, 2),
    }

    if ingreso_disponible <= 0:
        resultado.update(
            {
                "decision": "NO_PROCEDE",
                "mensaje": "Ingreso disponible insuficiente para cubrir gastos.",
            }
        )
        return resultado

    if cuota <= cuota_maxima:
        resultado.update(
            {
                "decision": "PROCEDE",
                "monto_aprobado_propuesto": round(monto_solicitado, 2),
                "mensaje": "Capacidad de pago suficiente. Puede promoverse a comité.",
            }
        )
        return resultado

    monto_reducido = round(monto_solicitado * REDUCCION_CONDICIONADO, 2)
    cuota_reducida = cuota_francesa(monto_reducido, plazo_meses, tea)

    if cuota_reducida <= cuota_maxima and monto_reducido >= producto.monto_min:
        resultado.update(
            {
                "decision": "CONDICIONAR",
                "monto_aprobado_propuesto": monto_reducido,
                "cuota_condicionada": cuota_reducida,
                "mensaje": (
                    f"Monto condicionado a S/ {monto_reducido:.2f} "
                    f"(cuota S/ {cuota_reducida:.2f})."
                ),
            }
        )
        return resultado

    resultado.update(
        {
            "decision": "NO_PROCEDE",
            "mensaje": "Cuota supera capacidad de pago incluso con monto reducido.",
        }
    )
    return resultado
