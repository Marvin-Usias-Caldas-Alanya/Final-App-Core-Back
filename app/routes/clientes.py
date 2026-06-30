from fastapi import APIRouter, HTTPException

from app.core.supabase import get_supabase

router = APIRouter()


@router.get("/{cliente_id}/productos")
async def productos_cliente(cliente_id: str) -> dict:
    try:
        supabase = get_supabase()

        cliente_resp = (
            supabase.table("clientes")
            .select("*")
            .eq("id", cliente_id)
            .maybe_single()
            .execute()
        )
        cliente = cliente_resp.data
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        creditos_resp = (
            supabase.table("creditos")
            .select("*")
            .eq("cliente_id", cliente_id)
            .order("created_at", desc=True)
            .execute()
        )

        solicitudes_resp = (
            supabase.table("solicitudes_credito")
            .select("*")
            .eq("cliente_id", cliente_id)
            .order("created_at", desc=True)
            .execute()
        )

        movimientos_resp = (
            supabase.table("movimientos")
            .select("*")
            .eq("cliente_id", cliente_id)
            .order("fecha_movimiento", desc=True)
            .execute()
        )

        return {
            "cliente": cliente,
            "creditos": creditos_resp.data or [],
            "solicitudes": solicitudes_resp.data or [],
            "movimientos": movimientos_resp.data or [],
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[ERROR] productos cliente {cliente_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Error al consultar productos del cliente",
        ) from exc
