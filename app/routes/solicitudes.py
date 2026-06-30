from fastapi import APIRouter, HTTPException

from app.core.supabase import get_supabase
from app.schemas.solicitudes import DesembolsoResponse, SolicitudResponse
from app.services.solicitudes_service import aprobar_solicitud, desembolsar_solicitud

router = APIRouter()


@router.post("/{solicitud_id}/aprobar", response_model=SolicitudResponse)
async def aprobar(solicitud_id: str) -> SolicitudResponse:
    try:
        supabase = get_supabase()
        solicitud = aprobar_solicitud(supabase, solicitud_id)
        return SolicitudResponse(solicitud=solicitud)
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[ERROR] aprobar solicitud {solicitud_id}: {exc}")
        raise HTTPException(status_code=500, detail="Error al aprobar solicitud") from exc


@router.post("/{solicitud_id}/desembolsar", response_model=DesembolsoResponse)
async def desembolsar(solicitud_id: str) -> DesembolsoResponse:
    try:
        supabase = get_supabase()
        result = desembolsar_solicitud(supabase, solicitud_id)
        return DesembolsoResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[ERROR] desembolsar solicitud {solicitud_id}: {exc}")
        raise HTTPException(status_code=500, detail="Error al desembolsar crédito") from exc
