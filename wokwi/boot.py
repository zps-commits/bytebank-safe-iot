"""Inicialização do Wi-Fi no ESP32. Não salva senhas no repositório."""
import network
import time
from config import WIFI_SSID, WIFI_PASSWORD

def conecta_wifi(timeout_ms=12000):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    print('Conectando Wi-Fi...')
    try:
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    except OSError as exc:
        print('Wi-Fi indisponível; funcionamento local habilitado:', exc)
        return False
    start = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        time.sleep_ms(300)
    if wlan.isconnected():
        print('Wi-Fi conectado, IP:', wlan.ifconfig()[0])
        return True
    print('Wi-Fi indisponível; funcionamento local habilitado')
    return False

conecta_wifi()
