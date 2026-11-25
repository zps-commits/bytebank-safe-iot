"""ByteBank Safe — Sprint 4: dashboard, comandos, pilha LIFO, detecção de envelope e telemetria HTTP.

Não movimenta dinheiro nem aciona uma fechadura real por padrão.
"""
import time
import machine
import network
import config
import _thread
try:
    from command_state import DiagnosticCounter
except ImportError:
    from esp32.command_state import DiagnosticCounter
import ujson
try:
    import urequests
except ImportError:
    import requests as urequests  # Alguns firmwares novos de MicroPython
from config import API_URL, DEVICE_ID, SIMULATE_ENVELOPE, ENABLE_RELAY, RELAY_ACTIVE_LEVEL

# GPIOs do ESP32 clássico. Verificar pinagem da placa antes de montar.
LED_OK = machine.Pin(2, machine.Pin.OUT)
LED_ALERT = machine.Pin(4, machine.Pin.OUT)
BTN_CONFIRM = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)
BTN_CANCEL = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
BTN_ENVELOPE = machine.Pin(27, machine.Pin.IN, machine.Pin.PULL_UP)
TRIG = machine.Pin(5, machine.Pin.OUT)
ECHO = machine.Pin(18, machine.Pin.IN)  # ECHO HC-SR04 5 V -> divisor para 3,3 V!
RELAY = machine.Pin(23, machine.Pin.OUT, value=1 - RELAY_ACTIVE_LEVEL)
TRIG.value(0)

# LIFO em RAM: append = push; pop = cancelamento do último lote pendente.
pendentes = []
# Eventos HTTP pendentes de retransmissão (FIFO em RAM; perde ao reiniciar).
fila_http = []
MAX_EVENTS = 50
next_seq = 0
state_lock = _thread.allocate_lock()
diagnostic = DiagnosticCounter()
latest_distance = None
# Nonce de boot evita repetir IDs baseados apenas no uptime após reinício.
import os
try:
    import ubinascii as binascii
except ImportError:
    import binascii
SESSION_ID = binascii.hexlify(os.urandom(6)).decode()


def event(kind, lote=None, extra=None):
    global next_seq
    next_seq += 1
    payload = {
        'event_id': '%s-%s-%d-%d' % (DEVICE_ID, SESSION_ID, time.ticks_ms(), next_seq),
        'device_id': DEVICE_ID,
        'type': kind,
        'pending_count': len(pendentes),
        'lote_id': lote,
        'uptime_ms': time.ticks_ms(),
    }
    if extra:
        payload.update(extra)
    if len(fila_http) >= MAX_EVENTS:
        # Segurança: não descartar silenciosamente; sinaliza e conserva o backlog.
        print('AVISO: fila HTTP cheia; evento não enfileirado:', kind)
        LED_ALERT.value(1)
        return False
    fila_http.append(payload)
    print('EVENTO:', ujson.dumps(payload))
    return True

def medir_distancia_cm():
    TRIG.value(0)
    time.sleep_us(2)
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)
    try:
        duracao_us = machine.time_pulse_us(ECHO, 1, 30000)
        if duracao_us < 0:
            return None
        return duracao_us / 58.0
    except (OSError, ValueError):
        return None

def registrar_envelope():
    if len(pendentes) >= 20:
        print('Limite de lotes atingido')
        LED_ALERT.value(1)
        return
    lote_id = '%s-%s-lote-%d' % (DEVICE_ID, SESSION_ID, next_seq + 1)
    # Não altera pilha se não houver capacidade para registrar o evento.
    if len(fila_http) >= MAX_EVENTS:
        print('Fila HTTP cheia: envelope não registrado')
        LED_ALERT.value(1)
        return
    pendentes.append(lote_id)
    event('deposit_detected', lote_id)
    diagnostic.detected()
    LED_OK.value(1)
    print('PUSH:', lote_id, '| Pilha:', len(pendentes))

def cancelar_ultimo():
    if not pendentes:
        print('Pilha vazia: nada a cancelar')
        return
    if len(fila_http) >= MAX_EVENTS:
        print('Fila HTTP cheia: cancelamento indisponível')
        LED_ALERT.value(1)
        return
    lote_id = pendentes.pop()
    event('deposit_cancelled', lote_id)
    LED_OK.value(bool(pendentes))
    print('POP:', lote_id)

def confirmar_lote():
    if not pendentes:
        print('Sem depósitos pendentes')
        return
    # Confirma somente o topo da pilha. Valor financeiro nunca é inferido do sensor.
    lote_id = pendentes[-1]
    if not event('deposit_confirmed', lote_id, {'pending_count': len(pendentes) - 1}):
        print('Sem espaço para registrar confirmação; operação mantida pendente')
        return
    pendentes.pop()
    LED_OK.value(bool(pendentes))
    print('CONFIRMADO localmente (não é crédito bancário):', lote_id)

def enviar_proximo():
    if not fila_http or not network.WLAN(network.STA_IF).isconnected():
        return
    with state_lock:
        payload = fila_http[0]
    response = None
    try:
        # DNS pode bloquear além do timeout de socket. Nesta sprint, use IPv4
        # numérico do servidor LAN; não resolver hostname dentro do loop.
        if not API_URL.startswith('http://'):
            raise ValueError('API_URL deve usar HTTP de laboratorio com IPv4 numerico')
        host = API_URL[7:].split('/', 1)[0].split(':', 1)[0]
        octets = host.split('.')
        if len(octets) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in octets):
            raise ValueError('API_URL exige IPv4 numerico do PC; hostname DNS nao suportado')
        response = urequests.post(API_URL, data=ujson.dumps(payload),
                                  headers={'Content-Type': 'application/json', 'X-API-Key': getattr(config, 'API_KEY', '')}, timeout=2)
        if 200 <= response.status_code < 300:
            print('HTTP OK:', response.status_code, payload['event_id'])
            with state_lock:
                fila_http.pop(0)
            if not fila_http:
                LED_ALERT.value(0)
        else:
            LED_ALERT.value(1)
            print('HTTP falhou (evento preservado):', response.status_code)
    except Exception as exc:
        LED_ALERT.value(1)
        print('Servidor indisponível (evento preservado):', exc)
    finally:
        if response is not None:
            response.close()

def server_request(method, path, body=None):
    # Nunca resolve hostname no loop de rede; configuração local deve usar IPv4.
    if not API_URL.startswith('http://'):
        raise ValueError('API_URL deve usar IPv4 HTTP na LAN')
    host=API_URL[7:].split('/',1)[0].split(':',1)[0]
    if len(host.split('.'))!=4 or not all(p.isdigit() and 0<=int(p)<=255 for p in host.split('.')):
        raise ValueError('API_URL exige IPv4 numerico')
    base=API_URL.rsplit('/',1)[0]
    headers={'Content-Type':'application/json'}
    token=getattr(config,'API_KEY','')
    if token: headers['X-API-Key']=token
    response=None
    try:
        if method=='GET':
            response=urequests.get(base+path,headers=headers,timeout=2)
        else:
            response=urequests.post(base+path,headers=headers,data=ujson.dumps(body),timeout=2)
        if not 200<=response.status_code<300:
            raise OSError('HTTP '+str(response.status_code))
        return response.json()
    finally:
        if response is not None: response.close()


def telemetry_snapshot():
    with state_lock:
        return {'device_id':DEVICE_ID,'uptime_ms':time.ticks_ms(),
                'pending_count':len(pendentes),'diagnostic_count':diagnostic.count,
                'queue_size':len(fila_http),'distance_cm':latest_distance,
                'source':'esp32_buttons' if SIMULATE_ENVELOPE else 'esp32_sensor'}


def sync_once():
    enviar_proximo()
    server_request('POST','/telemetry',telemetry_snapshot())
    command=server_request('GET','/commands/'+DEVICE_ID+'/next').get('command')
    if command:
        with state_lock:
            ack=diagnostic.apply(command,DEVICE_ID)
        server_request('POST','/commands/'+command['command_id']+'/ack',ack)
        server_request('POST','/telemetry',telemetry_snapshot())


def network_worker():
    wlan=network.WLAN(network.STA_IF)
    last_wifi=time.ticks_add(time.ticks_ms(),-10000)
    while True:
        try:
            now=time.ticks_ms()
            if not wlan.isconnected():
                if time.ticks_diff(now,last_wifi)>=10000:
                    last_wifi=now
                    wlan.active(True)
                    wlan.connect(config.WIFI_SSID,config.WIFI_PASSWORD)
            elif getattr(config,'HTTP_ENABLED',True):
                sync_once()
        except Exception as exc:
            print('Rede indisponivel; leitura local continua:',exc)
        time.sleep_ms(1000)


class DebouncedButton:
    """Estado estável por botão; pressionar só dispara uma vez até soltar."""
    def __init__(self, pin):
        self.pin = pin
        self.raw = pin.value()
        self.stable = 1
        self.changed_ms = time.ticks_ms()

    def pressed(self, now):
        value = self.pin.value()
        if value != self.raw:
            self.raw = value
            self.changed_ms = now
        if value != self.stable and time.ticks_diff(now, self.changed_ms) >= 35:
            self.stable = value
            return value == 0
        return False


class EnvelopeSensor:
    """Confirma presença e retirada em amostras válidas consecutivas."""
    def __init__(self):
        self.occupied = False
        self.streak = 0

    def detected(self, distance):
        if self.occupied:
            self.streak = self.streak + 1 if distance is not None and distance > 12 else 0
            if self.streak >= 3:
                self.occupied = False
                self.streak = 0
            return False

        self.streak = self.streak + 1 if distance is not None and 2 <= distance < 10 else 0
        if self.streak < 5:
            return False
        self.occupied = True
        self.streak = 0
        return True


def run():
    global latest_distance
    _thread.start_new_thread(network_worker, ())
    buttons = [DebouncedButton(pin) for pin in (BTN_ENVELOPE, BTN_CANCEL, BTN_CONFIRM)]
    last_sensor = time.ticks_ms()
    sensor = EnvelopeSensor()
    print('ByteBank Safe iniciado | simulacao:', SIMULATE_ENVELOPE)
    print('HTTP habilitado:', getattr(config, 'HTTP_ENABLED', True))
    while True:
        now = time.ticks_ms()
        hit_sim, hit_cancel, hit_confirm = [button.pressed(now) for button in buttons]
        detected = hit_sim if SIMULATE_ENVELOPE else False
        if not SIMULATE_ENVELOPE and time.ticks_diff(now, last_sensor) >= 80:
            last_sensor = now
            distance = medir_distancia_cm()
            latest_distance = distance
            detected = sensor.detected(distance)
        with state_lock:
            if detected:
                registrar_envelope()
            if hit_cancel:
                cancelar_ultimo()
            if hit_confirm:
                confirmar_lote()
        time.sleep_ms(10)


if __name__ == '__main__':
    run()

