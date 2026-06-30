import logging
from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount, Route
from supabase import create_client

from app.core.config import (
    SESSION_SECRET,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
    WEB_ADMIN_PASSWORD,
    WEB_ADMIN_USER,
    debug_env_payload,
    health_payload,
    refresh_env,
)
from app.routes import auth_api, clientes, health, originacion, pagos, solicitudes, tarifario

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

APP_DIR = Path(__file__).resolve().parent
MAIN_FILE = Path(__file__).resolve()

app = FastAPI(
    title="Core Mobile API",
    description="API central del ecosistema móvil Financiera Confianza",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

app.include_router(tarifario.router, tags=["tarifario"])
app.include_router(health.router, tags=["health"])
app.include_router(auth_api.router, prefix="/auth", tags=["auth"])
app.include_router(originacion.router, prefix="/originacion", tags=["originacion"])
app.include_router(solicitudes.router, prefix="/solicitudes", tags=["solicitudes"])
app.include_router(clientes.router, prefix="/clientes", tags=["clientes"])
app.include_router(pagos.router, prefix="/pagos", tags=["pagos"])

app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


def _collect_routes(routes, prefix: str = "") -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for route in routes:
        original = getattr(route, "original_router", None)
        if original is not None:
            ctx = getattr(route, "include_context", None)
            inc_prefix = getattr(ctx, "prefix", "") if ctx else ""
            items.extend(_collect_routes(original.routes, prefix + inc_prefix))
            continue

        path = getattr(route, "path", "") or ""
        full_path = (prefix + path).replace("//", "/") or "/"

        if isinstance(route, Mount):
            items.extend(_collect_routes(route.routes, full_path.rstrip("/")))
            continue

        if isinstance(route, Route):
            for method in sorted(route.methods or []):
                if method == "HEAD":
                    continue
                items.append({"method": method, "path": full_path})
            continue

        subroutes = getattr(route, "routes", None)
        if subroutes:
            items.extend(_collect_routes(subroutes, full_path))

    return items


@app.get("/routes-debug")
async def routes_debug() -> dict:
    routes = _collect_routes(app.routes)
    return {
        "main_file": str(MAIN_FILE),
        "count": len(routes),
        "routes": sorted(routes, key=lambda x: (x["path"], x["method"])),
    }


@app.on_event("startup")
async def startup_load_env() -> None:
    refresh_env()
    logging.getLogger(__name__).info("Core ejecutando desde: %s", MAIN_FILE)
    logging.getLogger(__name__).info(
        "Panel web: /login (→ /login-web), /dashboard-web, /solicitudes-web"
    )


@app.get("/health-direct")
async def health_direct() -> dict[str, str]:
    return health_payload()


@app.get("/debug-env-direct")
async def debug_env_direct() -> dict[str, str | bool]:
    return debug_env_payload()


# CORE WEB PANEL DIRECTO

refresh_env()
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    logging.getLogger(__name__).warning(
        "Core Web: SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados"
    )
core_db_web = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
    else None
)


def web_page(title: str, body: str) -> HTMLResponse:
    safe_title = escape(title)
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title} - Financiera Confianza</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #F4F7FA; color: #1a2b3c; }}
    a {{ color: #1464A5; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .header {{ background: linear-gradient(135deg, #004481, #1464A5, #2DCCCD); color: #fff; padding: 16px 24px; }}
    .header h1 {{ margin: 0; font-size: 1.2rem; }}
    .nav a {{ color: #fff; margin-right: 16px; font-weight: 600; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    .card {{ background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 4px 16px rgba(0,68,129,.08); margin-bottom: 16px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }}
    .stat {{ background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 2px 10px rgba(0,68,129,.06); }}
    .stat label {{ display: block; color: #64748b; font-size: 13px; margin-bottom: 6px; }}
    .stat strong {{ font-size: 22px; color: #004481; }}
    .btn {{ display: inline-block; background: #1464A5; color: #fff; padding: 10px 16px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; text-decoration: none; }}
    .btn:hover {{ background: #004481; color: #fff; text-decoration: none; }}
    .btn-success {{ background: #48AE64; }}
    .btn-danger {{ background: #D32F2F; }}
    .btn-warning {{ background: #F7893B; }}
    .btn-outline {{ background: #fff; color: #1464A5; border: 1px solid #1464A5; }}
    .btn-sm {{ padding: 6px 12px; font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e8eef5; text-align: left; font-size: 14px; }}
    th {{ background: #f8fbff; color: #004481; }}
    .error {{ background: #fdecea; color: #c62828; padding: 12px; border-radius: 8px; margin-bottom: 12px; }}
    .success {{ background: #e8f5e9; color: #2e7d32; padding: 12px; border-radius: 8px; margin-bottom: 12px; }}
    input {{ width: 100%; padding: 10px; margin: 6px 0 14px; border: 1px solid #cbd5e1; border-radius: 8px; }}
    label {{ font-weight: 600; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
    .login-box {{ max-width: 420px; margin: 60px auto; }}
  </style>
</head>
<body>{body}</body>
</html>"""
    )


def web_logged(request: Request) -> bool:
    return request.cookies.get("core_login") == "ok"


def _web_nav() -> str:
    return """
<div class="header">
  <h1>Core Mobile - Financiera Confianza</h1>
  <div class="nav" style="margin-top:8px">
    <a href="/dashboard-web">Dashboard</a>
    <a href="/solicitudes-web">Solicitudes</a>
    <a href="/logout-web">Cerrar sesión</a>
  </div>
</div>"""


def _web_guard(request: Request) -> RedirectResponse | None:
    if not web_logged(request):
        return RedirectResponse(url="/login-web", status_code=303)
    return None


def _fetch_solicitudes_web() -> list[dict[str, Any]]:
    if core_db_web is None:
        raise RuntimeError("Supabase no configurado en Core Web")
    result = (
        core_db_web.table("solicitudes_credito")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def _fetch_solicitud_web(solicitud_id: str) -> dict[str, Any] | None:
    if core_db_web is None:
        raise RuntimeError("Supabase no configurado en Core Web")
    return (
        core_db_web.table("solicitudes_credito")
        .select("*")
        .eq("id", solicitud_id)
        .maybe_single()
        .execute()
        .data
    )


def _stats_web(rows: list[dict[str, Any]]) -> dict[str, int]:
    stats = {
        "total": len(rows),
        "enviadas": 0,
        "aprobadas": 0,
        "rechazadas": 0,
        "desembolsadas": 0,
    }
    for row in rows:
        estado = (row.get("estado") or "").lower()
        if estado == "enviado":
            stats["enviadas"] += 1
        elif estado == "aprobado":
            stats["aprobadas"] += 1
        elif estado == "rechazado":
            stats["rechazadas"] += 1
        elif estado == "desembolsado":
            stats["desembolsadas"] += 1
    return stats


@app.get("/routes-debug-web")
async def routes_debug_web() -> list[str]:
    return [getattr(route, "path", str(route)) for route in app.routes]


@app.get("/")
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login-web", status_code=307)


@app.get("/login")
async def login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login-web", status_code=307)


@app.get("/login-web", response_class=HTMLResponse)
async def login_web_get() -> HTMLResponse:
    body = """
<div class="login-box card">
  <h2 style="margin-top:0;color:#004481">Core Web</h2>
  <p>Financiera Confianza</p>
  <form method="post" action="/login">
    <label for="usuario">Usuario</label>
    <input id="usuario" name="usuario" type="text" required>
    <label for="password">Contraseña</label>
    <input id="password" name="password" type="password" required>
    <button class="btn" type="submit" style="width:100%">Ingresar</button>
  </form>
</div>"""
    return web_page("Login", body)


async def _login_web_post(usuario: str, password: str):
    if usuario.strip() == WEB_ADMIN_USER and password == WEB_ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard-web", status_code=303)
        response.set_cookie("core_login", "ok", httponly=True, samesite="lax")
        return response

    body = """
<div class="login-box card">
  <div class="error">Credenciales incorrectas.</div>
  <p><a href="/login">Volver al login</a></p>
</div>"""
    return web_page("Login error", body)


@app.post("/login-web")
async def login_web_post(usuario: str = Form(...), password: str = Form(...)):
    return await _login_web_post(usuario, password)


@app.post("/login")
async def login_post(usuario: str = Form(...), password: str = Form(...)):
    return await _login_web_post(usuario, password)


@app.get("/logout-web")
async def logout_web() -> RedirectResponse:
    response = RedirectResponse(url="/login-web", status_code=303)
    response.delete_cookie("core_login")
    return response


@app.get("/dashboard-web", response_class=HTMLResponse)
async def dashboard_web(request: Request):
    guard = _web_guard(request)
    if guard:
        return guard

    error = ""
    try:
        rows = _fetch_solicitudes_web()
        stats = _stats_web(rows)
    except Exception as exc:
        logging.getLogger(__name__).exception("Dashboard web")
        stats = _stats_web([])
        error = f'<div class="error">Error Supabase: {escape(str(exc))}</div>'

    body = f"""
{_web_nav()}
<div class="wrap">
  <h2>Dashboard</h2>
  {error}
  <div class="cards">
    <div class="stat"><label>Total</label><strong>{stats["total"]}</strong></div>
    <div class="stat"><label>Enviadas</label><strong>{stats["enviadas"]}</strong></div>
    <div class="stat"><label>Aprobadas</label><strong>{stats["aprobadas"]}</strong></div>
    <div class="stat"><label>Rechazadas</label><strong>{stats["rechazadas"]}</strong></div>
    <div class="stat"><label>Desembolsadas</label><strong>{stats["desembolsadas"]}</strong></div>
  </div>
  <a class="btn" href="/solicitudes-web">Ver solicitudes</a>
</div>"""
    return web_page("Dashboard", body)


@app.get("/solicitudes-web", response_class=HTMLResponse)
async def solicitudes_web_list(request: Request):
    guard = _web_guard(request)
    if guard:
        return guard

    error = ""
    try:
        rows = _fetch_solicitudes_web()
    except Exception as exc:
        logging.getLogger(__name__).exception("Solicitudes web")
        rows = []
        error = f'<div class="error">Error Supabase: {escape(str(exc))}</div>'

    table_rows = ""
    for s in rows:
        sid = escape(str(s.get("id", "")))
        table_rows += f"""
<tr>
  <td>{escape(str(s.get("numero_expediente") or "—"))}</td>
  <td>{escape(str(s.get("monto_solicitado") or "—"))}</td>
  <td>{escape(str(s.get("plazo_meses") or "—"))}</td>
  <td>{escape(str(s.get("estado") or "—"))}</td>
  <td>{escape(str(s.get("created_at") or "—"))[:16]}</td>
  <td><a class="btn btn-outline btn-sm" href="/solicitudes-web/{sid}">Ver</a></td>
</tr>"""

    body = f"""
{_web_nav()}
<div class="wrap">
  <h2>Solicitudes</h2>
  {error}
  <div class="card" style="padding:0;overflow:auto">
    <table>
      <thead>
        <tr>
          <th>Expediente</th>
          <th>Monto</th>
          <th>Plazo</th>
          <th>Estado</th>
          <th>Fecha</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {table_rows or '<tr><td colspan="6">No hay solicitudes</td></tr>'}
      </tbody>
    </table>
  </div>
</div>"""
    return web_page("Solicitudes", body)


@app.get("/solicitudes-web/{solicitud_id}", response_class=HTMLResponse)
async def solicitud_web_detalle(request: Request, solicitud_id: str):
    guard = _web_guard(request)
    if guard:
        return guard

    try:
        solicitud = _fetch_solicitud_web(solicitud_id)
    except Exception as exc:
        body = f'{_web_nav()}<div class="wrap"><div class="error">{escape(str(exc))}</div></div>'
        return web_page("Error", body)

    if not solicitud:
        body = f'{_web_nav()}<div class="wrap"><div class="error">Solicitud no encontrada.</div><a href="/solicitudes-web">Volver</a></div>'
        return web_page("Detalle", body)

    estado = (solicitud.get("estado") or "").lower()
    sid = escape(solicitud_id)
    actions = ""

    if estado == "enviado":
        actions = f"""
<form method="post" action="/solicitudes-web/{sid}/aprobar" style="display:inline">
  <button class="btn btn-success" type="submit">Aprobar</button>
</form>
<form method="post" action="/solicitudes-web/{sid}/rechazar" style="display:inline">
  <button class="btn btn-danger" type="submit">Rechazar</button>
</form>"""
    elif estado == "aprobado":
        actions = f"""
<form method="post" action="/solicitudes-web/{sid}/desembolsar">
  <button class="btn btn-warning" type="submit">Desembolsar</button>
</form>"""
    elif estado == "desembolsado":
        actions = '<div class="success">Solicitud desembolsada.</div>'

    body = f"""
{_web_nav()}
<div class="wrap">
  <h2>Detalle solicitud</h2>
  <div class="card">
    <p><strong>Expediente:</strong> {escape(str(solicitud.get("numero_expediente") or "—"))}</p>
    <p><strong>Estado:</strong> {escape(str(solicitud.get("estado") or "—"))}</p>
    <p><strong>Monto solicitado:</strong> {escape(str(solicitud.get("monto_solicitado") or "—"))}</p>
    <p><strong>Monto aprobado:</strong> {escape(str(solicitud.get("monto_aprobado") or "—"))}</p>
    <p><strong>Plazo:</strong> {escape(str(solicitud.get("plazo_meses") or "—"))} meses</p>
    <p><strong>Cuota estimada:</strong> {escape(str(solicitud.get("cuota_estimada") or "—"))}</p>
    <p><strong>Destino:</strong> {escape(str(solicitud.get("destino_credito") or "—"))}</p>
    <div class="actions">{actions}</div>
    <p style="margin-top:16px"><a href="/solicitudes-web">Volver</a></p>
  </div>
</div>"""
    return web_page("Detalle", body)


@app.post("/solicitudes-web/{solicitud_id}/aprobar")
async def solicitud_web_aprobar(request: Request, solicitud_id: str):
    guard = _web_guard(request)
    if guard:
        return guard

    try:
        solicitud = _fetch_solicitud_web(solicitud_id)
        if solicitud and core_db_web:
            monto = solicitud.get("monto_solicitado")
            core_db_web.table("solicitudes_credito").update(
                {"estado": "aprobado", "monto_aprobado": monto}
            ).eq("id", solicitud_id).execute()
    except Exception:
        logging.getLogger(__name__).exception("Aprobar web %s", solicitud_id)

    return RedirectResponse(url=f"/solicitudes-web/{solicitud_id}", status_code=303)


@app.post("/solicitudes-web/{solicitud_id}/rechazar")
async def solicitud_web_rechazar(request: Request, solicitud_id: str):
    guard = _web_guard(request)
    if guard:
        return guard

    try:
        if core_db_web:
            core_db_web.table("solicitudes_credito").update(
                {
                    "estado": "rechazado",
                    "motivo_rechazo": "Rechazado desde Core Web",
                }
            ).eq("id", solicitud_id).execute()
    except Exception:
        logging.getLogger(__name__).exception("Rechazar web %s", solicitud_id)

    return RedirectResponse(url=f"/solicitudes-web/{solicitud_id}", status_code=303)


@app.post("/solicitudes-web/{solicitud_id}/desembolsar")
async def solicitud_web_desembolsar(request: Request, solicitud_id: str):
    guard = _web_guard(request)
    if guard:
        return guard

    try:
        if core_db_web:
            core_db_web.table("solicitudes_credito").update(
                {"estado": "desembolsado"}
            ).eq("id", solicitud_id).execute()
    except Exception:
        logging.getLogger(__name__).exception("Desembolsar web %s", solicitud_id)

    return RedirectResponse(url=f"/solicitudes-web/{solicitud_id}", status_code=303)
