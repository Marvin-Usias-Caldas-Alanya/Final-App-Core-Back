"""Simulación de buró crediticio según último dígito del documento (30 casos académicos)."""

from __future__ import annotations

from typing import Any


def _ultimo_digito(numero_documento: str) -> int:
    limpio = "".join(c for c in numero_documento if c.isdigit())
    if not limpio:
        raise ValueError("Número de documento inválido")
    return int(limpio[-1])


def simular_buro(numero_documento: str) -> dict[str, Any]:
    """
    Regla académica: la calificación depende del último dígito del DNI/RUC.

    - 7 → PERDIDA + lista inhabilitados (casos 28)
    - 4 → DUDOSO (casos 29-30)
    - 2, 8 → CPP (casos 26-27)
    - 5 → DEFICIENTE (caso 25)
    - resto → NORMAL
    """
    digito = _ultimo_digito(numero_documento)

    if digito == 7:
        return {
            "numero_documento": numero_documento,
            "calificacion_sbs": "PERDIDA",
            "dias_atraso_maximo": 120,
            "entidades_reportadas": 3,
            "lista_inhabilitados": True,
            "recomendacion": "RECHAZAR",
            "mensaje": "Cliente en lista de inhabilitados. Operación no procede.",
        }

    if digito == 4:
        return {
            "numero_documento": numero_documento,
            "calificacion_sbs": "DUDOSO",
            "dias_atraso_maximo": 95,
            "entidades_reportadas": 2,
            "lista_inhabilitados": False,
            "recomendacion": "RECHAZAR",
            "mensaje": "Calificación DUDOSO con mora severa. Rechazo recomendado.",
        }

    if digito in (2, 8):
        dias = 15 if digito == 2 else 20
        return {
            "numero_documento": numero_documento,
            "calificacion_sbs": "CPP",
            "dias_atraso_maximo": dias,
            "entidades_reportadas": 1,
            "lista_inhabilitados": False,
            "recomendacion": "CONDICIONAR",
            "mensaje": f"Calificación CPP ({dias} días mora). Condicionar monto/plazo.",
        }

    if digito == 5:
        return {
            "numero_documento": numero_documento,
            "calificacion_sbs": "DEFICIENTE",
            "dias_atraso_maximo": 45,
            "entidades_reportadas": 1,
            "lista_inhabilitados": False,
            "recomendacion": "CONDICIONAR",
            "mensaje": "Calificación DEFICIENTE. Condicionar operación.",
        }

    entidades = 0 if digito in (0, 3) else 1
    return {
        "numero_documento": numero_documento,
        "calificacion_sbs": "NORMAL",
        "dias_atraso_maximo": 0,
        "entidades_reportadas": entidades,
        "lista_inhabilitados": False,
        "recomendacion": "PROCEDER",
        "mensaje": "Sin observaciones relevantes en buró simulado.",
    }
