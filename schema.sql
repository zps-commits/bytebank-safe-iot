CREATE TABLE IF NOT EXISTS saldos (
    device_id TEXT PRIMARY KEY,
    envelopes_confirmados INTEGER NOT NULL DEFAULT 0 CHECK (envelopes_confirmados >= 0)
);

CREATE TABLE IF NOT EXISTS transacoes (
    device_id TEXT NOT NULL REFERENCES saldos(device_id),
    lote_id TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('pendente', 'cancelado', 'confirmado')),
    PRIMARY KEY (device_id, lote_id)
);

CREATE TABLE IF NOT EXISTS logs_auditoria (
    event_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    lote_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    dados_json TEXT NOT NULL,
    recebido_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id, lote_id) REFERENCES transacoes(device_id, lote_id)
);


-- Sprint 4: estado observado e histórico de telemetria (sem valores monetários).
CREATE TABLE IF NOT EXISTS telemetria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    uptime_ms INTEGER NOT NULL,
    pending_count INTEGER NOT NULL,
    diagnostic_count INTEGER NOT NULL,
    queue_size INTEGER NOT NULL,
    distance_cm REAL,
    source TEXT NOT NULL,
    recebido_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_telemetria_device ON telemetria(device_id, id DESC);
CREATE TABLE IF NOT EXISTS comandos (
    command_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action = 'reset_counter'),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','applied','failed')),
    resultado_json TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmado_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_comandos_device ON comandos(device_id, status);
