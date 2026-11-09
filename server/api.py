"""API da Sprint 3. O saldo representa envelopes, em unidades inteiras."""
from contextlib import asynccontextmanager, closing
import os
from pathlib import Path
import sqlite3
from typing import Annotated

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, StringConstraints

SCHEMA = Path(__file__).resolve().parents[1] / "schema.sql"
IDENTIFIER = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
# Busca em tabela hash por tipo de evento, O(1) esperado.
TRANSITIONS = {
    "deposit_detected": (None, "pendente"),
    "deposit_cancelled": ("pendente", "cancelado"),
    "deposit_confirmed": ("pendente", "confirmado"),
}


class Event(BaseModel):
    event_id: IDENTIFIER
    device_id: IDENTIFIER
    lote_id: IDENTIFIER
    type: IDENTIFIER
    pending_count: int = Field(strict=True, ge=0, le=20)
    uptime_ms: int | None = Field(default=None, strict=True, ge=0)


def connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def create_app(path=None):
    db_path = path if path is not None else os.environ.get("SAFE_DB", "bytebank-safe.sqlite3")

    @asynccontextmanager
    async def lifespan(app):
        with closing(connect(db_path)) as db:
            db.executescript(SCHEMA.read_text(encoding="utf-8"))
        yield

    app = FastAPI(title="ByteBank Safe", version="3.0", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "module": "ByteBank Safe", "sprint": 3}

    @app.post("/events", status_code=201, responses={200: {"description": "Evento já recebido"}})
    def post_event(event: Event, response: Response):
        transition = TRANSITIONS.get(event.type)
        if transition is None:
            raise HTTPException(422, "Tipo de evento inválido")
        expected, new_state = transition
        payload = event.model_dump_json()

        with closing(connect(db_path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT dados_json FROM logs_auditoria WHERE event_id = ?", (event.event_id,)
            ).fetchone()
            if previous:
                if Event.model_validate_json(previous["dados_json"]) != event:
                    raise HTTPException(409, "event_id já usado com dados diferentes")
                response.status_code = 200
                return {"status": "duplicate", "event_id": event.event_id}

            lot = (event.device_id, event.lote_id)
            current = db.execute(
                "SELECT estado FROM transacoes WHERE device_id = ? AND lote_id = ?", lot
            ).fetchone()
            if (current["estado"] if current else None) != expected:
                raise HTTPException(409, "Transição inválida para o estado atual do lote")

            if expected is None:
                db.execute("INSERT OR IGNORE INTO saldos (device_id) VALUES (?)", (event.device_id,))
                db.execute("INSERT INTO transacoes VALUES (?, ?, ?)", (*lot, new_state))
            else:
                db.execute("UPDATE transacoes SET estado = ? WHERE device_id = ? AND lote_id = ?",
                           (new_state, *lot))
            if new_state == "confirmado":
                db.execute("UPDATE saldos SET envelopes_confirmados = envelopes_confirmados + 1 "
                           "WHERE device_id = ?", (event.device_id,))
            db.execute("INSERT INTO logs_auditoria (event_id, device_id, lote_id, tipo, dados_json) "
                       "VALUES (?, ?, ?, ?, ?)", (event.event_id, *lot, event.type, payload))
        return {"status": "received", "event_id": event.event_id}

    @app.get("/events")
    def list_events():
        with closing(connect(db_path)) as db:
            events = db.execute("SELECT event_id, device_id, lote_id, tipo, recebido_em "
                                "FROM logs_auditoria ORDER BY rowid DESC LIMIT 100").fetchall()
            count = db.execute("SELECT COUNT(*) FROM logs_auditoria").fetchone()[0]
        return {"events": [dict(event) for event in events], "count": count}

    @app.get("/balances/{device_id}")
    def balance(device_id: str):
        with closing(connect(db_path)) as db:
            row = db.execute("SELECT envelopes_confirmados FROM saldos WHERE device_id = ?",
                             (device_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Dispositivo sem saldo cadastrado")
        return {"device_id": device_id, "envelopes_confirmados": row["envelopes_confirmados"]}

    return app


app = create_app()
