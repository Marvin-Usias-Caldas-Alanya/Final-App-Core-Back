"""
Tarifario oficial Financiera Confianza (Perú).

Fuente: T001-019 Tarifario de Tasas Activas (vigencia a partir de enero 2026,
aprobado 22.12.2025).
https://confianza.pe/docs/2026/01/T001-019%20Tarifario%20de%20tasas%20activas.pdf

Ejemplo referencial Crédito Personal (web oficial):
https://confianza.pe/persona/credito-personal
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

TARIFARIO_VERSION = "T001-019"
TARIFARIO_VIGENCIA = "2026-01"
TARIFARIO_FUENTE = (
    "https://confianza.pe/docs/2026/01/T001-019%20Tarifario%20de%20tasas%20activas.pdf"
)

# Parámetros transversales publicados por Financiera Confianza
DIAS_BASE_ANIO = 360
ITF_PORCENTAJE = 0.005
TASA_MORATORIA_TNA = 12.54  # Tasa Nominal Anual - moneda nacional


@dataclass(frozen=True)
class ProductoTarifario:
    codigo: str
    nombre: str
    tea_maxima: float
    tea_referencial: float
    monto_min: float
    monto_max: float
    plazo_min_meses: int
    plazo_max_meses: int
    moneda: str = "PEN"
    notas: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _producto(
    codigo: str,
    nombre: str,
    tea_maxima: float,
    *,
    tea_referencial: float = 56.0,
    monto_min: float = 300.0,
    monto_max: float = 20000.0,
    plazo_min_meses: int = 3,
    plazo_max_meses: int = 36,
    notas: str = "",
) -> ProductoTarifario:
    return ProductoTarifario(
        codigo=codigo,
        nombre=nombre,
        tea_maxima=tea_maxima,
        tea_referencial=tea_referencial,
        monto_min=monto_min,
        monto_max=monto_max,
        plazo_min_meses=plazo_min_meses,
        plazo_max_meses=plazo_max_meses,
        notas=notas,
    )


PRODUCTOS: dict[str, ProductoTarifario] = {
    "credito_microempresa": _producto(
        "credito_microempresa",
        "Crédito Empresarial Microempresa",
        tea_maxima=43.92,
        tea_referencial=43.92,
        monto_min=1000.0,
        monto_max=20000.0,
        plazo_min_meses=3,
        plazo_max_meses=36,
        notas=(
            "Banco Andino — TEA 43.92% sin desgravamen / 40.92% con desgravamen. "
            "Caso verificación: S/ 1,000 · 12 meses · cuota S/ 100.95."
        ),
    ),
    "construyendo_confianza": _producto(
        "construyendo_confianza",
        "Construyendo Confianza",
        tea_maxima=82.0,
        notas="Incluye Agua y Saneamiento.",
    ),
    "creditos_inclusion": _producto(
        "creditos_inclusion",
        "Créditos de Inclusión",
        tea_maxima=105.0,
        notas="Incluye Iniciando Oficios, Palabra de Mujer, Paralelo PDM.",
    ),
    "creditos_personales": _producto(
        "creditos_personales",
        "Créditos Personales",
        tea_maxima=87.65,
        tea_referencial=56.0,
        notas=(
            "TEA referencial 56% según ejemplo oficial S/ 1,000 a 12 meses "
            "(cuota S/ 105.81, TCEA 57.54%)."
        ),
    ),
    "creditos_pymes": _producto(
        "creditos_pymes",
        "Créditos Pymes",
        tea_maxima=90.0,
        notas=(
            "Incluye Iniciando Confianza, Iniciando Negocios, "
            "Emprendiendo Confianza, Emprendiendo Mujer."
        ),
    ),
    "credito_agropecuario": _producto(
        "credito_agropecuario",
        "Crédito Agropecuario",
        tea_maxima=90.0,
    ),
}

PRODUCTO_DEFAULT = "credito_microempresa"
TEA_CON_DESGRAVAMEN = 40.92
TEA_SIN_DESGRAVAMEN = 43.92

# Mapeo tipo_negocio del cliente → producto tarifario
TIPO_NEGOCIO_A_PRODUCTO: dict[str, str] = {
    "microempresa": "credito_microempresa",
    "pyme": "creditos_pymes",
    "negocio": "creditos_pymes",
    "comercio": "creditos_pymes",
    "servicios": "creditos_pymes",
    "agropecuario": "credito_agropecuario",
    "agricola": "credito_agropecuario",
    "inclusion": "creditos_inclusion",
    "personal": "creditos_personales",
    "consumo": "creditos_personales",
    "vivienda": "construyendo_confianza",
    "construccion": "construyendo_confianza",
}


def resolver_producto(tipo_negocio: str | None = None, codigo: str | None = None) -> ProductoTarifario:
    if codigo and codigo in PRODUCTOS:
        return PRODUCTOS[codigo]

    if tipo_negocio:
        key = tipo_negocio.strip().lower().replace(" ", "_")
        producto_codigo = TIPO_NEGOCIO_A_PRODUCTO.get(key, PRODUCTO_DEFAULT)
        return PRODUCTOS[producto_codigo]

    return PRODUCTOS[PRODUCTO_DEFAULT]


def validar_solicitud(
    monto: float,
    plazo_meses: int,
    tipo_negocio: str | None = None,
    codigo_producto: str | None = None,
) -> tuple[ProductoTarifario, list[str]]:
    producto = resolver_producto(tipo_negocio, codigo_producto)
    errores: list[str] = []

    if monto < producto.monto_min:
        errores.append(f"Monto mínimo: S/ {producto.monto_min:.2f}")
    if monto > producto.monto_max:
        errores.append(f"Monto máximo referencial: S/ {producto.monto_max:.2f}")
    if plazo_meses < producto.plazo_min_meses:
        errores.append(f"Plazo mínimo: {producto.plazo_min_meses} meses")
    if plazo_meses > producto.plazo_max_meses:
        errores.append(f"Plazo máximo referencial: {producto.plazo_max_meses} meses")

    return producto, errores


def tarifario_payload() -> dict[str, Any]:
    return {
        "version": TARIFARIO_VERSION,
        "vigencia": TARIFARIO_VIGENCIA,
        "fuente": TARIFARIO_FUENTE,
        "parametros_globales": {
            "dias_base_anio": DIAS_BASE_ANIO,
            "itf_porcentaje": ITF_PORCENTAJE,
            "tasa_moratoria_tna": TASA_MORATORIA_TNA,
            "sistema_amortizacion": "frances",
        },
        "producto_default": PRODUCTO_DEFAULT,
        "productos": [p.to_dict() for p in PRODUCTOS.values()],
    }
