import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import WEB_ADMIN_PASSWORD, WEB_ADMIN_USER
from app.core.supabase import get_supabase_admin
from app.services.solicitudes_service import (
    aprobar_solicitud,
    desembolsar_solicitud,
    rechazar_solicitud,
)

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

router = APIRouter(include_in_schema=False)


def _currency(value: Any) -> str:
    try:
        return f"S/ {float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _datetime_fmt(value: Any) -> str:
    if not value:
        return "—"
    text = str(value).replace("T", " ")
    if "+" in text:
        text = text.split("+")[0]
    if "." in text:
        text = text.split(".")[0]
    return text[:16]


def _estado_badge(estado: str | None) -> str:
    mapping = {
        "enviado": "badge-enviado",
        "recibido_comite": "badge-enviado",
        "aprobado": "badge-aprobado",
        "rechazado": "badge-rechazado",
        "desembolsado": "badge-desembolsado",
        "condicionado": "badge-condicionado",
    }
    return mapping.get((estado or "").lower(), "badge-default")


templates.env.filters["currency"] = _currency
templates.env.filters["datetime_fmt"] = _datetime_fmt
templates.env.filters["estado_badge"] = _estado_badge


def _logged_in(request: Request) -> bool:
    return bool(request.session.get("user"))


def _require_session(request: Request) -> RedirectResponse | None:
    if not _logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


def _flash(request: Request, message: str, level: str = "info") -> None:
    request.session["flash"] = message
    request.session["flash_type"] = level


def _pop_flash(request: Request) -> tuple[str | None, str]:
    return request.session.pop("flash", None), request.session.pop("flash_type", "info")


def _cliente_nombre(cliente: dict[str, Any] | None) -> str:
    if not cliente:
        return "—"
    nombre = f"{cliente.get('nombres', '')} {cliente.get('apellidos', '')}".strip()
    return nombre or "—"


def _asesor_nombre(asesor: dict[str, Any] | None) -> str:
    if not asesor:
        return "—"
    nombre = f"{asesor.get('nombres', '')} {asesor.get('apellidos', '')}".strip()
    codigo = asesor.get("codigo_empleado")
    if nombre and codigo:
        return f"{nombre} ({codigo})"
    return nombre or str(codigo or "—")


def _fetch_cliente(cliente_id: Any) -> dict[str, Any] | None:
    if not cliente_id:
        return None
    return (
        get_supabase_admin()
        .table("clientes")
        .select("*")
        .eq("id", cliente_id)
        .maybe_single()
        .execute()
        .data
    )


def _fetch_asesor(asesor_id: Any) -> dict[str, Any] | None:
    if not asesor_id:
        return None
    return (
        get_supabase_admin()
        .table("asesores_negocio")
        .select("*")
        .eq("id", asesor_id)
        .maybe_single()
        .execute()
        .data
    )


def _fetch_solicitudes_enriched() -> list[dict[str, Any]]:
    rows = (
        get_supabase_admin()
        .table("solicitudes_credito")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )

    cache: dict[str, dict[str, Any] | None] = {}
    enriched: list[dict[str, Any]] = []

    for row in rows:
        cid = row.get("cliente_id")
        key = str(cid) if cid is not None else ""
        if key not in cache:
            cache[key] = _fetch_cliente(cid)
        cliente = cache[key]
        enriched.append(
            {
                **row,
                "cliente": cliente,
                "cliente_nombre": _cliente_nombre(cliente),
                "cliente_dni": (cliente or {}).get("numero_documento", "—"),
            }
        )

    return enriched


def _dashboard_stats(solicitudes: list[dict[str, Any]]) -> dict[str, Any]:
    stats = {
        "total": len(solicitudes),
        "enviadas": 0,
        "aprobadas": 0,
        "rechazadas": 0,
        "desembolsadas": 0,
        "monto_total_solicitado": 0.0,
    }
    for row in solicitudes:
        estado = (row.get("estado") or "").lower()
        stats["monto_total_solicitado"] += float(row.get("monto_solicitado") or 0)
        if estado == "enviado":
            stats["enviadas"] += 1
        elif estado == "aprobado":
            stats["aprobadas"] += 1
        elif estado == "rechazado":
            stats["rechazadas"] += 1
        elif estado == "desembolsado":
            stats["desembolsadas"] += 1
    return stats


@router.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)


@router.get("/login")
async def login_get(request: Request):
    if _logged_in(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    flash, flash_type = _pop_flash(request)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": flash if flash_type == "error" else None, "flash": flash if flash_type != "error" else None},
    )


@router.post("/login")
async def login_post(
    request: Request,
    usuario: str = Form(...),
    password: str = Form(...),
):
    if usuario.strip() == WEB_ADMIN_USER and password == WEB_ADMIN_PASSWORD:
        request.session["user"] = "admin"
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Usuario o contraseña incorrectos."},
        status_code=401,
    )


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/dashboard")
async def dashboard(request: Request):
    redirect = _require_session(request)
    if redirect:
        return redirect

    flash, flash_type = _pop_flash(request)
    try:
        solicitudes = _fetch_solicitudes_enriched()
        stats = _dashboard_stats(solicitudes)
        db_error = None
    except Exception as exc:
        logger.exception("Error dashboard")
        stats = _dashboard_stats([])
        db_error = str(exc)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "stats": stats,
            "flash": flash,
            "flash_type": flash_type,
            "db_error": db_error,
            "active": "dashboard",
        },
    )


@router.get("/solicitudes-web")
async def solicitudes_web(request: Request):
    redirect = _require_session(request)
    if redirect:
        return redirect

    flash, flash_type = _pop_flash(request)
    try:
        solicitudes = _fetch_solicitudes_enriched()
        db_error = None
    except Exception as exc:
        logger.exception("Error solicitudes-web")
        solicitudes = []
        db_error = str(exc)

    return templates.TemplateResponse(
        request,
        "solicitudes.html",
        {
            "solicitudes": solicitudes,
            "flash": flash,
            "flash_type": flash_type,
            "db_error": db_error,
            "active": "solicitudes",
        },
    )


@router.get("/solicitudes-web/{solicitud_id}")
async def solicitud_detalle(request: Request, solicitud_id: str):
    redirect = _require_session(request)
    if redirect:
        return redirect

    flash, flash_type = _pop_flash(request)
    try:
        solicitud = (
            get_supabase_admin()
            .table("solicitudes_credito")
            .select("*")
            .eq("id", solicitud_id)
            .maybe_single()
            .execute()
            .data
        )
        if not solicitud:
            _flash(request, "Solicitud no encontrada.", "error")
            return RedirectResponse(url="/solicitudes-web", status_code=303)

        cliente = _fetch_cliente(solicitud.get("cliente_id"))
        asesor = _fetch_asesor(solicitud.get("asesor_id"))
        estado = (solicitud.get("estado") or "").lower()
        db_error = None
    except Exception as exc:
        logger.exception("Error detalle solicitud")
        _flash(request, f"Error al cargar solicitud: {exc}", "error")
        return RedirectResponse(url="/solicitudes-web", status_code=303)

    return templates.TemplateResponse(
        request,
        "solicitud_detalle.html",
        {
            "solicitud": solicitud,
            "cliente": cliente,
            "cliente_nombre": _cliente_nombre(cliente),
            "asesor_nombre": _asesor_nombre(asesor),
            "estado": estado,
            "puede_aprobar": estado == "enviado",
            "puede_rechazar": estado == "enviado",
            "puede_desembolsar": estado == "aprobado",
            "flash": flash,
            "flash_type": flash_type,
            "db_error": db_error,
            "active": "solicitudes",
        },
    )


@router.post("/solicitudes-web/{solicitud_id}/aprobar")
async def aprobar_web(request: Request, solicitud_id: str):
    redirect = _require_session(request)
    if redirect:
        return redirect

    try:
        aprobar_solicitud(get_supabase_admin(), solicitud_id)
        _flash(request, "Solicitud aprobada correctamente.", "success")
    except HTTPException as exc:
        _flash(request, str(exc.detail), "error")
    except Exception as exc:
        logger.exception("Aprobar web")
        _flash(request, str(exc), "error")

    return RedirectResponse(url=f"/solicitudes-web/{solicitud_id}", status_code=303)


@router.post("/solicitudes-web/{solicitud_id}/rechazar")
async def rechazar_web(request: Request, solicitud_id: str):
    redirect = _require_session(request)
    if redirect:
        return redirect

    try:
        rechazar_solicitud(get_supabase_admin(), solicitud_id)
        _flash(request, "Solicitud rechazada.", "success")
    except HTTPException as exc:
        _flash(request, str(exc.detail), "error")
    except Exception as exc:
        logger.exception("Rechazar web")
        _flash(request, str(exc), "error")

    return RedirectResponse(url=f"/solicitudes-web/{solicitud_id}", status_code=303)


@router.post("/solicitudes-web/{solicitud_id}/desembolsar")
async def desembolsar_web(request: Request, solicitud_id: str):
    redirect = _require_session(request)
    if redirect:
        return redirect

    try:
        desembolsar_solicitud(
            get_supabase_admin(),
            solicitud_id,
            notificacion_mensaje="Tu crédito fue desembolsado desde Financiera Confianza.",
        )
        _flash(request, "Crédito desembolsado. Crédito, cronograma y movimiento generados.", "success")
    except HTTPException as exc:
        _flash(request, str(exc.detail), "error")
    except Exception as exc:
        logger.exception("Desembolsar web")
        _flash(request, str(exc), "error")

    return RedirectResponse(url=f"/solicitudes-web/{solicitud_id}", status_code=303)
