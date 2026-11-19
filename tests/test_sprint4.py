"""Integração real por HTTP + SQLite + AppTest; ESP32 substituída por GPIO/rede de PC."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import requests
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from server.api import create_app, connect
from esp32.command_state import DiagnosticCounter
import test_firmware as firmware_tests

ROOT=Path(__file__).resolve().parents[1]

class Sprint4APITests(unittest.TestCase):
    def setUp(self):
        folder=self.enterContext(TemporaryDirectory())
        self.path=Path(folder)/'safe.sqlite3'
        self.client=self.enterContext(TestClient(create_app(self.path)))
        self.command={'command_id':'cmd-1','device_id':'safe-01','action':'reset_counter'}
    def test_retries_ack_and_persistence(self):
        c=self.client
        self.assertEqual(c.post('/commands',json=self.command).status_code,201)
        self.assertEqual(c.post('/commands',json=self.command).status_code,200)
        self.assertEqual(c.post('/commands',json={**self.command,'device_id':'other'}).status_code,409)
        for _ in range(2): self.assertEqual(c.get('/commands/safe-01/next').json()['command'],self.command)
        self.assertIsNone(c.get('/commands/other/next').json()['command'])
        ack={'device_id':'other','status':'applied','diagnostic_count':0}
        self.assertEqual(c.post('/commands/cmd-1/ack',json=ack).status_code,404)
        ack['device_id']='safe-01'
        self.assertEqual(c.post('/commands/cmd-1/ack',json=ack).status_code,200)
        self.assertTrue(c.post('/commands/cmd-1/ack',json=ack).json()['duplicate'])
        self.assertEqual(c.post('/commands/cmd-1/ack',json={**ack,'diagnostic_count':2}).status_code,409)
        with TestClient(create_app(self.path)) as restarted:
            self.assertIsNone(restarted.get('/commands/safe-01/next').json()['command'])
    def test_invalid_payloads_and_laboratory_key(self):
        self.assertEqual(self.client.post('/telemetry',json={}).status_code,422)
        self.assertEqual(self.client.post('/commands',json={**self.command,'action':'unlock'}).status_code,422)
        with patch.dict(os.environ,{'SAFE_API_KEY':'test-only-key'}):
            self.assertEqual(self.client.post('/commands',json=self.command).status_code,401)
            self.assertEqual(self.client.post('/commands',json=self.command,headers={'X-API-Key':'test-only-key'}).status_code,201)
    def test_dashboard_empty_and_missing_database(self):
        with patch.dict(os.environ,{'SAFE_DB':str(self.path)}):
            at=AppTest.from_file(str(ROOT/'dashboard/app.py')).run(timeout=10)
            self.assertFalse(at.exception)
            self.assertIn('Nenhum dispositivo',at.info[0].value)
        with patch.dict(os.environ,{'SAFE_DB':str(self.path)+'.missing'}):
            at=AppTest.from_file(str(ROOT/'dashboard/app.py')).run(timeout=10)
            self.assertFalse(at.exception)
            self.assertIn('Banco indisponível',at.error[0].value)

class CommandStateTests(unittest.TestCase):
    def test_reset_cache_survives_restart_without_reapplying(self):
        with TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'cache.json')
            counter=DiagnosticCounter(path); counter.detected();counter.detected()
            command={'command_id':'reset-1','device_id':'safe-01','action':'reset_counter'}
            ack=counter.apply(command,'safe-01'); self.assertEqual(counter.count,0)
            counter.detected(); self.assertEqual(counter.apply(command,'safe-01'),ack)
            self.assertEqual(counter.count,1)
            restarted=DiagnosticCounter(path);restarted.detected()
            self.assertEqual(restarted.apply(command,'safe-01'),ack)
            self.assertEqual(restarted.count,1)
            with self.assertRaises(ValueError): restarted.apply(command,'other')

class EndToEndTests(unittest.TestCase):
    def test_dashboard_http_firmware_ack_database_and_recovery(self):
        with TemporaryDirectory() as tmp:
            db_path=Path(tmp)/'e2e.sqlite3'
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
            base=f'http://127.0.0.1:{port}'
            env={**os.environ,'SAFE_DB':str(db_path),'SAFE_API_KEY':''}
            log=open(Path(tmp)/'server.log','w')
            proc=subprocess.Popen([sys.executable,'-m','uvicorn','server.api:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
            evidence={'origin':'Integração PC: HTTP real, SQLite e Streamlit AppTest; GPIO e rede da ESP32 substituídos. Não é bancada física.','steps':[]}
            def note(step, **data): evidence['steps'].append(dict(step=step,**data))
            try:
                deadline=time.monotonic()+10
                while True:
                    try:
                        if requests.get(base+'/health',timeout=.3).status_code==200: break
                    except requests.RequestException: pass
                    if time.monotonic()>deadline: self.fail('API não iniciou')
                    time.sleep(.05)
                harness=firmware_tests.TestFirmware('test_lifo_and_confirmation_count')
                harness.setUp()
                try:
                    f=harness.f
                    f.API_URL=base+'/events';f.urequests=requests
                    f.diagnostic=DiagnosticCounter(str(Path(tmp)/'ack-cache.json'))
                    f.registrar_envelope();harness.clock+=1;f.registrar_envelope()
                    f.cancelar_ultimo();f.confirmar_lote()
                    for _ in range(4): f.enviar_proximo()
                    state=f.telemetry_snapshot();state['source']='simulator_pc'
                    self.assertEqual(requests.post(base+'/telemetry',json=state,timeout=2).status_code,201)
                    note('firmware_events',queue=len(f.fila_http),pending=len(f.pendentes),counter=f.diagnostic.count)
                    self.assertEqual(len(f.fila_http),0)
                    self.assertEqual(f.diagnostic.count,2)
                finally: harness.tearDown()
                with patch.dict(os.environ,{'SAFE_DB':str(db_path),'SAFE_API_BASE':base,'SAFE_API_KEY':''}):
                    at=AppTest.from_file(str(ROOT/'dashboard/app.py')).run(timeout=10)
                    self.assertFalse(at.exception)
                    metrics={m.label:str(m.value) for m in at.metric}
                    self.assertEqual(metrics['Confirmados no banco'],'1')
                    self.assertEqual(metrics['Cancelados no banco'],'1')
                    self.assertEqual(metrics['Contador de diagnóstico'],'2')
                    at.button(key='reset_counter').click().run(timeout=10)
                    self.assertFalse(at.exception)
                    command=requests.get(base+'/commands/test-safe/next',timeout=2).json()['command']
                    self.assertIsNotNone(command)
                    note('streamlit_button',command=command,metrics=metrics)
                    # Ciclo de rede real do firmware, executado no PC com GPIO substituído.
                    original_snapshot=f.telemetry_snapshot
                    f.telemetry_snapshot=lambda: {**original_snapshot(),'source':'simulator_pc'}
                    f.sync_once()
                    self.assertEqual(f.diagnostic.count,0)
                    self.assertEqual(f.pendentes,[])
                    # Perda de ACK: uma repetição usa o resultado salvo e não reaplica reset.
                    f.diagnostic.detected()
                    cached=f.diagnostic.apply(command,'test-safe')
                    self.assertEqual(cached['diagnostic_count'],0)
                    self.assertEqual(f.diagnostic.count,1)
                    at.run(timeout=10)
                    self.assertFalse(at.exception)
                    self.assertEqual(next(m.value for m in at.metric if m.label=='Contador de diagnóstico'),'0')
                    self.assertIsNone(requests.get(base+'/commands/test-safe/next',timeout=2).json()['command'])
                    with closing(connect(db_path)) as db:
                        row=dict(db.execute('SELECT * FROM comandos').fetchone())
                        self.assertEqual(row['status'],'applied')
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM logs_auditoria').fetchone()[0],4)
                        self.assertEqual(db.execute('SELECT envelopes_confirmados FROM saldos').fetchone()[0],1)
                    note('ack_visible_in_database_and_dashboard',status=row['status'],counter=0,audit_events=4)
                    # API fora do ar: página continua lendo o banco e mostra falha de envio.
                    proc.terminate();proc.wait(timeout=5)
                    at.button(key='reset_counter').click().run(timeout=10)
                    self.assertFalse(at.exception)
                    self.assertTrue(any('Não foi possível' in e.value for e in at.error))
                    note('api_offline',dashboard_crashed=False,send_error_visible=True)
                evidence['result']='PASSOU'
                evidence['time_utc']=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
                folder=ROOT/'docs/evidencias';folder.mkdir(exist_ok=True)
                (folder/'e2e_sprint4.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
            finally:
                if proc.poll() is None: proc.terminate();proc.wait(timeout=5)
                log.close()
