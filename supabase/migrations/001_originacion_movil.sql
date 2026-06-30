-- Migración originación móvil (ejecutar en Supabase SQL Editor)
-- Campos opcionales en solicitudes_credito y cartera_diaria

ALTER TABLE solicitudes_credito
  ADD COLUMN IF NOT EXISTS canal_origen TEXT DEFAULT 'asesor_app',
  ADD COLUMN IF NOT EXISTS con_desgravamen BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS latitud_visita DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS longitud_visita DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS fecha_visita TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS observaciones_asesor TEXT,
  ADD COLUMN IF NOT EXISTS motivo_condicion TEXT,
  ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT;

ALTER TABLE cartera_diaria
  ADD COLUMN IF NOT EXISTS solicitud_id UUID REFERENCES solicitudes_credito(id),
  ADD COLUMN IF NOT EXISTS latitud_visita DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS longitud_visita DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS fecha_visita TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS sync_outbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entidad TEXT NOT NULL,
  entidad_id UUID NOT NULL,
  accion TEXT NOT NULL,
  payload JSONB DEFAULT '{}',
  estado_sync TEXT DEFAULT 'pendiente',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Índice para cartera por asesor
CREATE INDEX IF NOT EXISTS idx_cartera_asesor ON cartera_diaria(asesor_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_canal ON solicitudes_credito(canal_origen, estado);
