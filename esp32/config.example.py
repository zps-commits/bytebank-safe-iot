# Copie para config.py no ESP32. Nunca publique config.py com credenciais.
WIFI_SSID = 'SUA_REDE_WIFI'
WIFI_PASSWORD = 'SUA_SENHA_WIFI'
# IP LAN da máquina executando o servidor: NÃO use localhost no ESP32.
API_URL = 'http://192.168.1.100:8000/events'
DEVICE_ID = 'safe-01'
# Para testes sem sensor, mantenha True e use o botão GPIO 27.
SIMULATE_ENVELOPE = True
# Só habilitar após conferir tensão, relé, trava e isolamento da montagem.
ENABLE_RELAY = False
# Nível elétrico que aciona relé (módulos típicos podem ser ativo em LOW).
RELAY_ACTIVE_LEVEL = 0

# False permite testar a pilha offline; a fila permanece em RAM.
HTTP_ENABLED = True
