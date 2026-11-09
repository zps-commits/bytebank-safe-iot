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
