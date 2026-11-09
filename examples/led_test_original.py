from machine import Pin
import time

# O LED integrado na maioria dos ESP32 fica no Pino 2
led = Pin(2, Pin.OUT)

print("🚀 MicroPython operacional no ESP32!")

# Pisca o LED 5 vezes para confirmar o funcionamento
for i in range(5):
    led.value(1) # Liga o LED
    print(f"Piscou {i+1}/5 - LED LIGADO")
    time.sleep(0.5)
    led.value(0) # Desliga o LED
    time.sleep(0.5)

print("✅ Teste concluído com sucesso!")