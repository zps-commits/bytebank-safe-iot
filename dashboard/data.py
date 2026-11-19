"""Consultas curtas diretamente no SQLite; sem conexão global entre threads."""
from contextlib import closing
from pathlib import Path
import sqlite3
from urllib.request import Request, urlopen
import json
import os

def snapshot(path, device_id=None):
    uri=Path(path).resolve().as_uri()+'?mode=ro'
    with closing(sqlite3.connect(uri, uri=True, timeout=2)) as db:
        db.row_factory=sqlite3.Row
        with db:
            devices=[r[0] for r in db.execute('SELECT device_id FROM saldos UNION SELECT device_id FROM telemetria ORDER BY 1')]
            selected=device_id if device_id in devices else (devices[0] if devices else None)
            def rows(sql): return [dict(r) for r in db.execute(sql,(selected,))]
            telemetry=rows('SELECT * FROM telemetria WHERE device_id=? ORDER BY id DESC LIMIT 100')
            lots=rows('SELECT estado, COUNT(*) AS quantidade FROM transacoes WHERE device_id=? GROUP BY estado')
            events=rows('SELECT event_id, lote_id, tipo, recebido_em FROM logs_auditoria WHERE device_id=? ORDER BY rowid DESC LIMIT 30')
            commands=rows('SELECT command_id, action, status, criado_em, confirmado_em, resultado_json FROM comandos WHERE device_id=? ORDER BY rowid DESC LIMIT 20')
    return dict(devices=devices,selected=selected,telemetry=telemetry,lots=lots,events=events,commands=commands)

def send_command(base_url, device_id, command_id):
    body={'device_id': device_id, 'command_id': command_id, 'action': 'reset_counter'}
    headers={'Content-Type':'application/json'}
    if os.getenv('SAFE_API_KEY'): headers['X-API-Key']=os.environ['SAFE_API_KEY']
    request=Request(base_url.rstrip('/')+'/commands',data=json.dumps(body).encode(),headers=headers,method='POST')
    with urlopen(request,timeout=3) as response: return json.load(response)
