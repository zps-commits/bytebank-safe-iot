"""Telemetria e comandos persistentes; registra ACK sem confundir envio e execução."""
from contextlib import closing
import json
from typing import Literal
from fastapi import HTTPException, Response
from pydantic import BaseModel, Field
from server.api_types import IDENTIFIER

class Telemetry(BaseModel):
    device_id: IDENTIFIER
    uptime_ms: int = Field(strict=True, ge=0)
    pending_count: int = Field(strict=True, ge=0, le=20)
    diagnostic_count: int = Field(strict=True, ge=0)
    queue_size: int = Field(strict=True, ge=0, le=50)
    distance_cm: float | None = Field(default=None, ge=0, le=600)
    source: Literal['esp32_buttons', 'esp32_sensor', 'simulator_pc']

class Command(BaseModel):
    command_id: IDENTIFIER
    device_id: IDENTIFIER
    action: Literal['reset_counter']

class Acknowledgement(BaseModel):
    device_id: IDENTIFIER
    status: Literal['applied', 'failed']
    diagnostic_count: int = Field(strict=True, ge=0)
    message: str = Field(default='', max_length=200)


def register_routes(app, db_path, connect):
    @app.post('/telemetry', status_code=201)
    def telemetry(body: Telemetry):
        with closing(connect(db_path)) as db, db:
            db.execute('INSERT INTO telemetria (device_id, uptime_ms, pending_count, diagnostic_count, '
                       'queue_size, distance_cm, source) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       tuple(body.model_dump().values()))
            # Histórico limitado; não apaga auditoria de depósitos nem comandos.
            db.execute('DELETE FROM telemetria WHERE device_id=? AND id NOT IN '
                       '(SELECT id FROM telemetria WHERE device_id=? ORDER BY id DESC LIMIT 1000)',
                       (body.device_id, body.device_id))
        return {'status': 'received'}

    @app.post('/commands', status_code=201)
    def command(body: Command, response: Response):
        with closing(connect(db_path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM comandos WHERE command_id=?',(body.command_id,)).fetchone()
            if row:
                if row['device_id'] != body.device_id or row['action'] != body.action:
                    raise HTTPException(409, 'Identificador de comando em conflito')
                response.status_code=200
                return dict(row)
            db.execute('INSERT INTO comandos (command_id, device_id, action) VALUES (?, ?, ?)',
                       (body.command_id, body.device_id, body.action))
        return {**body.model_dump(), 'status': 'pending'}

    @app.get('/commands/{device_id}/next')
    def next_command(device_id: str):
        with closing(connect(db_path)) as db:
            row=db.execute("SELECT command_id, device_id, action FROM comandos "
                           "WHERE device_id=? AND status='pending' ORDER BY rowid LIMIT 1",
                           (device_id,)).fetchone()
        # Continua pendente até ACK; falha de rede não perde o comando.
        return {'command': dict(row) if row else None}

    @app.post('/commands/{command_id}/ack')
    def acknowledge(command_id: str, body: Acknowledgement):
        payload=body.model_dump_json()
        with closing(connect(db_path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM comandos WHERE command_id=?',(command_id,)).fetchone()
            if not row or row['device_id'] != body.device_id:
                raise HTTPException(404, 'Comando não encontrado para este dispositivo')
            if row['status'] != 'pending':
                if json.loads(row['resultado_json']) != body.model_dump():
                    raise HTTPException(409, 'ACK já registrado com resultado diferente')
                return {'status': row['status'], 'duplicate': True}
            db.execute('UPDATE comandos SET status=?, resultado_json=?, confirmado_em=CURRENT_TIMESTAMP '
                       'WHERE command_id=?',(body.status,payload,command_id))
        return {'status': body.status, 'duplicate': False}
