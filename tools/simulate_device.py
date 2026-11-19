"""Simulador explícito de PC para demonstração sem a placa. Não é evidência física."""
import argparse
import json
from pathlib import Path
import sys
import time
from uuid import uuid4
from urllib.request import Request, urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from esp32.command_state import DiagnosticCounter
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--api',default='http://127.0.0.1:8000')
parser.add_argument('--device',default='demo-pc')
args=parser.parse_args()

def call(method,path,body=None):
    import os
    headers={'Content-Type':'application/json'}
    if os.getenv('SAFE_API_KEY'): headers['X-API-Key']=os.environ['SAFE_API_KEY']
    request=Request(args.api.rstrip('/')+path,data=json.dumps(body).encode() if body else None,headers=headers,method=method)
    with urlopen(request,timeout=3) as response: return json.load(response)

with tempfile.TemporaryDirectory() as folder:
    counter=DiagnosticCounter(str(Path(folder)/'commands.json'))
    lot='demo-'+str(uuid4())
    # Um depósito confirmado permite ver estado persistido no dashboard.
    for kind,pending in [('deposit_detected',1),('deposit_confirmed',0)]:
        call('POST','/events',{'event_id':str(uuid4()),'device_id':args.device,'lote_id':lot,
                             'type':kind,'pending_count':pending,'uptime_ms':0})
    counter.detected()
    started=time.monotonic()
    print('SIMULADOR PC: dados marcados simulator_pc. Ctrl+C para parar.')
    try:
        while True:
            try:
                call('POST','/telemetry',{'device_id':args.device,'uptime_ms':int((time.monotonic()-started)*1000),
                     'pending_count':0,'diagnostic_count':counter.count,'queue_size':0,
                     'distance_cm':None,'source':'simulator_pc'})
                command=call('GET','/commands/'+args.device+'/next')['command']
                if command:
                    ack=counter.apply(command,args.device)
                    call('POST','/commands/'+command['command_id']+'/ack',ack)
                    print('ACK:',ack)
            except Exception as exc: print('Rede indisponível; próxima tentativa em 1 s:',exc)
            time.sleep(1)
    except KeyboardInterrupt: print('Simulação encerrada.')
