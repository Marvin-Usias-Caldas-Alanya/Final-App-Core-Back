from fastapi import APIRouter, HTTPException, Query

from app.core.tarifario import resolver_producto, tarifario_payload

router = APIRouter()


@router.get("/tarifario")
async def obtener_tarifario() -> dict:
    return tarifario_payload()


@router.get("/tarifario/producto")
async def obtener_producto_tarifario(
    tipo_negocio: str | None = Query(default=None),
    codigo: str | None = Query(default=None),
) -> dict:
    try:
        producto = resolver_producto(tipo_negocio=tipo_negocio, codigo=codigo)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Producto tarifario no encontrado") from exc
    return producto.to_dict()
