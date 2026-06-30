from fastapi import APIRouter, HTTPException

from app.core.supabase import get_supabase
from app.schemas.pagos import MensajeResponse, PagoCuotaResponse
from app.services.pagos_service import pagar_cuota_demo

router = APIRouter()


@router.post(
    "/credito/{credito_id}/pagar-cuota-demo",
    response_model=PagoCuotaResponse | MensajeResponse,
)
async def pagar_cuota(credito_id: str) -> PagoCuotaResponse | MensajeResponse:
    try:
        supabase = get_supabase()
        result = pagar_cuota_demo(supabase, credito_id)

        if result.get("cuota") is None:
            return MensajeResponse(message=result["message"])

        return PagoCuotaResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[ERROR] pagar cuota demo credito {credito_id}: {exc}")
        raise HTTPException(status_code=500, detail="Error al registrar pago") from exc
