"""Regressões no PC com GPIO, relógio e rede substituídos; não são teste físico."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

class Pin:
    OUT, IN, PULL_UP = 1, 2, 3
    def __init__(self, number, mode, pull=None, value=None):
        self.current = (1 if mode == self.IN else 0) if value is None else value
    def value(self, value=None):
        if value is not None: self.current = int(value)
        return self.current

class TestFirmware(unittest.TestCase):
    def setUp(self):
        self.clock = 1000; self.connected = True
        fake_time = types.SimpleNamespace(ticks_ms=lambda:self.clock,
            ticks_diff=lambda a,b:a-b, ticks_add=lambda a,b:a+b)
        config = types.SimpleNamespace(API_URL='http://127.0.0.1:8000/events', DEVICE_ID='test-safe',
            SIMULATE_ENVELOPE=True, ENABLE_RELAY=False, RELAY_ACTIVE_LEVEL=0)
        self.response = types.SimpleNamespace(status_code=201, close=lambda:None)
        self.sent=[]
        def post(url, **kwargs):
            self.assertEqual(kwargs['timeout'], 2)
            self.sent.append(json.loads(kwargs['data']))
            return self.response
        self.patch=patch.dict(sys.modules, {
            'time':fake_time,'machine':types.SimpleNamespace(Pin=Pin),
            'network':types.SimpleNamespace(STA_IF=0,WLAN=lambda _:types.SimpleNamespace(isconnected=lambda:self.connected)),
            'config':config,'ujson':json,'urequests':types.SimpleNamespace(post=post)})
        self.patch.start()
        spec=importlib.util.spec_from_file_location('safe_test',Path(__file__).parents[1]/'esp32/main.py')
        self.f=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.f)
    def tearDown(self): self.patch.stop()
    def test_lifo_and_confirmation_count(self):
        f=self.f; f.registrar_envelope(); first=f.pendentes[0]
        self.clock+=1; f.registrar_envelope(); second=f.pendentes[-1]
        f.cancelar_ultimo(); f.confirmar_lote()
        self.assertEqual([e['lote_id'] for e in f.fila_http],[first,second,second,first])
        self.assertEqual([e['pending_count'] for e in f.fila_http],[1,2,1,0])
        self.assertEqual(f.pendentes,[]); self.assertEqual(f.LED_OK.value(),0)
    def test_full_queue_preserves_stack(self):
        f=self.f; f.registrar_envelope(); original=f.pendentes[:]
        f.fila_http *= f.MAX_EVENTS
        f.cancelar_ultimo(); f.confirmar_lote(); f.registrar_envelope()
        self.assertEqual(f.pendentes,original)
        self.assertEqual(len(f.fila_http),f.MAX_EVENTS)
    def test_empty_and_stack_limit(self):
        f=self.f; f.cancelar_ultimo(); f.confirmar_lote(); self.assertEqual(f.fila_http,[])
        for i in range(21): self.clock+=1; f.registrar_envelope()
        self.assertEqual(len(f.pendentes),20); self.assertEqual(len(f.fila_http),20)
    def test_failed_http_retains_event_and_success_removes(self):
        f=self.f; f.registrar_envelope(); self.response.status_code=503; f.enviar_proximo()
        self.assertEqual(len(f.fila_http),1)
        self.response.status_code=201; f.enviar_proximo(); self.assertEqual(len(f.fila_http),0)
    def test_hostname_rejected_before_dns(self):
        self.f.registrar_envelope(); self.f.API_URL='http://host.wokwi.internal:8000/events'
        self.f.enviar_proximo()
        self.assertEqual(self.sent,[]); self.assertEqual(len(self.f.fila_http),1)
        self.assertEqual(self.f.LED_ALERT.value(),1)
    def test_disconnected_does_not_send(self):
        self.f.registrar_envelope(); self.connected=False; self.f.enviar_proximo()
        self.assertEqual(self.sent,[]); self.assertEqual(len(self.f.fila_http),1)
    def test_button_bounce_hold_and_repress(self):
        pin=Pin(27,Pin.IN); button=self.f.DebouncedButton(pin)
        pin.value(0); self.assertFalse(button.pressed(1010))
        pin.value(1); self.assertFalse(button.pressed(1020))
        pin.value(0); self.assertFalse(button.pressed(1030))
        self.assertTrue(button.pressed(1065)); self.assertFalse(button.pressed(1100))
        pin.value(1); button.pressed(1200); button.pressed(1235)
        pin.value(0); button.pressed(1300); self.assertTrue(button.pressed(1335))

if __name__=='__main__': unittest.main()
