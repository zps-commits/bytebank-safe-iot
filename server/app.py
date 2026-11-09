"""Servidor HTTP de testes do ByteBank Safe (stdlib, sem dependências).

POST /events recebe telemetria JSON, GET /events e /health permitem auditoria.
O log JSONL não é banco de dados nem registra valores financeiros.
"""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
import json
import os

STORE = Path(os.environ.get('SAFE_EVENTS_FILE', str(Path(__file__).parent / 'events.jsonl')))
LOCK = Lock()
ALLOWED = {'deposit_detected', 'deposit_cancelled', 'deposit_confirmed'}

def process_event(data):
    if not isinstance(data, dict):
        return 400, {'error': 'Corpo precisa ser JSON'}
    if not all(isinstance(data.get(k), str) and data.get(k) for k in ('event_id', 'device_id', 'type')):
        return 400, {'error': 'event_id, device_id e type são obrigatórios'}
    if data['type'] not in ALLOWED:
        return 422, {'error': 'Tipo de evento inválido'}
    count = data.get('pending_count')
    if type(count) is not int or not 0 <= count <= 20:
        return 422, {'error': 'pending_count deve ser inteiro de 0 a 20'}
    record = dict(data)
    record['received_at_utc'] = datetime.now(timezone.utc).isoformat()
    with LOCK:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        if STORE.exists():
            with STORE.open(encoding='utf-8') as f:
                for line in f:
                    if json.loads(line).get('event_id') == data['event_id']:
                        return 200, {'status': 'duplicate', 'event_id': data['event_id']}
        with STORE.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print('EVENTO RECEBIDO:', record, flush=True)
    return 201, {'status': 'received', 'event_id': data['event_id']}

def events_list():
    if not STORE.exists():
        return {'events': [], 'count': 0}
    with LOCK:
        with STORE.open(encoding='utf-8') as f:
            records = [json.loads(line) for line in f if line.strip()]
    return {'events': records[-100:], 'count': len(records)}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == '/health':
            self.send_json(200, {'status':'ok', 'module':'ByteBank Safe', 'sprint':2})
        elif self.path == '/events':
            self.send_json(200, events_list())
        else:
            self.send_json(404, {'error':'Rota não encontrada'})

    def do_POST(self):
        if self.path != '/events':
            return self.send_json(404, {'error':'Rota não encontrada'})
        try:
            size = int(self.headers.get('Content-Length', 0))
        except ValueError:
            return self.send_json(400, {'error':'Content-Length inválido'})
        if not 0 < size <= 4096:
            return self.send_json(413, {'error':'Tamanho de payload inválido'})
        try:
            data = json.loads(self.rfile.read(size))
        except (UnicodeDecodeError, ValueError):
            return self.send_json(400, {'error':'JSON inválido'})
        status, response = process_event(data)
        self.send_json(status, response)

def run(host='0.0.0.0', port=8000):
    server = ThreadingHTTPServer((host, port), Handler)
    print('ByteBank Safe HTTP: http://%s:%s' % (host, server.server_port), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()

if __name__ == '__main__':
    run()
