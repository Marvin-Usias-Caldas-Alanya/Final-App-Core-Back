# Core Mobile API — Financiera Confianza

Backend FastAPI conectado a Supabase. Centraliza operaciones de negocio para `app_fuerza_ventas` y `app_clientes`.

**Solo este servicio** debe usar `SUPABASE_SERVICE_ROLE_KEY`. Las apps Flutter usan la clave anon/publishable.

## Requisitos

- Python 3.11+
- Acceso a proyecto Supabase (URL + service role key)

## Instalación

```bash
cd core_mobile_api
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Variables de entorno

Copie `.env.example` a `.env` en esta carpeta:

```env
SUPABASE_URL=https://fwhlotcagzqgyzqupynp.supabase.co
SUPABASE_ANON_KEY=sb_publishable_y9WiJ32w9ucUOaM11Ee4HQ_waDaHC-3
SUPABASE_SERVICE_ROLE_KEY=valor_del_service_role
API_ENV=dev
```

| Variable | Descripción |
|----------|-------------|
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_ANON_KEY` | Clave publishable (referencia; la API usa service role) |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave service role (**solo backend**) |
| `API_ENV` | Entorno (`dev`, `prod`) |

## Ejecutar

Desde `core_mobile_api`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Documentación interactiva: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Endpoints

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servicio y Supabase |

Respuesta:

```json
{
  "status": "ok",
  "service": "core_mobile_api",
  "supabase": "configured"
}
```

### Solicitudes

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/solicitudes/{solicitud_id}/aprobar` | Aprueba solicitud (`estado=aprobado`, `monto_aprobado`) |
| POST | `/solicitudes/{solicitud_id}/desembolsar` | Desembolsa: crédito + cronograma + movimiento |

### Clientes

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/clientes/{cliente_id}/productos` | Cliente, créditos, solicitudes y movimientos |

Movimientos ordenados por `fecha_movimiento` descendente.

### Pagos

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/pagos/credito/{credito_id}/pagar-cuota-demo` | Paga la primera cuota pendiente (demo) |

## Probar desde PC

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/solicitudes/{UUID}/aprobar

curl -X POST http://localhost:8000/solicitudes/{UUID}/desembolsar

curl http://localhost:8000/clientes/{UUID}/productos

curl -X POST http://localhost:8000/pagos/credito/{UUID}/pagar-cuota-demo
```

También puede usar Swagger en `/docs`.

## Probar desde celular (misma red Wi‑Fi)

1. Obtenga la IP local del PC:
   - Windows: `ipconfig` → IPv4 (ej. `192.168.1.50`)
   - Linux/macOS: `ip addr` o `ifconfig`
2. Ejecute la API con `--host 0.0.0.0 --port 8000`
3. Desde el navegador del celular: `http://192.168.1.50:8000/health`
4. En Flutter (cuando se integre), base URL: `http://192.168.1.50:8000`

Asegúrese de permitir el puerto 8000 en el firewall de Windows si no responde.

## Desplegar en Render

Repositorio: [Final-App-Core](https://github.com/Marvin-Usias-Caldas-Alanya/Final-App-Core)

### Opción A — Blueprint (`render.yaml`)

1. Entra a [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**
2. Conecta el repo `Marvin-Usias-Caldas-Alanya/Final-App-Core`
3. Render detectará `render.yaml` y creará el servicio web
4. Completa las variables marcadas como secretas:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `WEB_ADMIN_PASSWORD`
5. **Create Blueprint** → espera el deploy

### Opción B — Web Service manual

| Campo | Valor |
|-------|-------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |

Variables de entorno: las mismas que en `.env.example` (`API_ENV=production`).

### Verificar

- `https://TU-SERVICIO.onrender.com/health`
- `https://TU-SERVICIO.onrender.com/login` (panel web)

En las apps Flutter, actualiza `CORE_API_URL` con la URL de Render.

> **Nota:** el plan free de Render puede tardar ~30 s en responder tras inactividad (cold start).

## Estructura

```
core_mobile_api/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── supabase.py
│   ├── routes/
│   │   ├── health.py
│   │   ├── solicitudes.py
│   │   ├── clientes.py
│   │   └── pagos.py
│   ├── schemas/
│   │   ├── solicitudes.py
│   │   └── pagos.py
│   └── services/
│       ├── solicitudes_service.py
│       ├── creditos_service.py
│       └── pagos_service.py
├── requirements.txt
├── .env.example
└── README_CORE.md
```

## Notas

- Errores de negocio devuelven `HTTPException` sin stack trace al cliente.
- Logs útiles se imprimen en consola del servidor.
- La tabla `notificaciones` es opcional al desembolsar; si no existe, el desembolso continúa.
