# Arquitetura atual — Parcial 4

ESP32 coleta entradas e mantém pilha LIFO/FIFO em RAM. Uma thread separada envia eventos e telemetria à FastAPI, que grava SQLite. O Streamlit consulta o mesmo banco a cada 2 s e cria comandos pela API. A ESP32 busca o próximo comando, aplica um reset de contador diagnóstico e envia ACK. O dashboard acompanha `pending`, `applied` e `failed`.

O saldo mede envelopes confirmados, não valores financeiros. O reset preserva depósitos e auditoria. Não há acionamento de trava nesta implementação. Rede local de laboratório, com chave opcional; integração física completa pendente.

Veja [guia da Parcial 4](ENTREGA_SPRINT4.md), [schema](../schema.sql), [API](../server/api.py) e [teste integrado](evidencias/e2e_sprint4.json).
