import logging
from datetime import UTC, datetime
from typing import Any

from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

DEFAULT_TEA = 45.0
PRODUCTO_NOMBRE = "Microcrédito Confianza"


def tasa_mensual(tea_percent: float) -> float:
    tea = tea_percent / 100
    return (1 + tea) ** (1 / 12) - 1


def cuota_francesa(monto: float, plazo_meses: int, tea_percent: float = DEFAULT_TEA) -> float:
    if monto <= 0 or plazo_meses <= 0:
        return 0.0

    tasa = tasa_mensual(tea_percent)
    if tasa == 0:
        return round(monto / plazo_meses, 2)

    factor = (1 + tasa) ** plazo_meses
    cuota = monto * tasa * factor / (factor - 1)
    return round(cuota, 2)


def generar_cronograma(
    credito_id: str,
    monto: float,
    plazo_meses: int,
    tea_percent: float,
    fecha_base: datetime | None = None,
) -> list[dict[str, Any]]:
    if plazo_meses <= 0:
        return []

    base = fecha_base or datetime.now(UTC)
    tasa = tasa_mensual(tea_percent)
    cuota_mensual = cuota_francesa(monto, plazo_meses, tea_percent)
    saldo = monto
    cuotas: list[dict[str, Any]] = []

    for numero in range(1, plazo_meses + 1):
        interes = round(saldo * tasa, 2)
        capital = round(cuota_mensual - interes, 2)
        saldo = round(max(0.0, saldo - capital), 2)
        vencimiento = base + relativedelta(months=numero)

        cuotas.append(
            {
                "credito_id": credito_id,
                "numero_cuota": numero,
                "fecha_vencimiento": vencimiento.date().isoformat(),
                "capital": capital,
                "interes": interes,
                "cuota": cuota_mensual,
                "saldo": saldo,
                "estado": "pendiente",
                "monto_pagado": 0,
                "dias_mora": 0,
            }
        )

    return cuotas
