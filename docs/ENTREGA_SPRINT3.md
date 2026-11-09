# Entrega Parcial 3 · API e persistência

Requer Python 3.11 ou superior. Na raiz do repositório:

```bash
python -m pip install -r requirements.txt
python -m uvicorn server.api:app --host 0.0.0.0 --port 8000
```

A API cria `bytebank-safe.sqlite3` no primeiro início. Use a variável de ambiente `SAFE_DB` para selecionar outro arquivo. O firmware usa a configuração `API_URL='http://IP-LAN-DO-PC:8000/events'`. A API é didática e deve ser usada em rede de teste. A interface de documentação está em `http://localhost:8000/docs`.

| Rota | Função |
|---|---|
| POST /events | Valida evento MicroPython. 201 novo, 200 repetição idêntica, 409 conflito e 422 payload inválido. |
| GET /events | Exibe registros recentes da auditoria e a contagem total. |
| GET /balances/{device_id} | Exibe o total de envelopes confirmados para o dispositivo. |
| GET /health | Verifica a disponibilidade. |

A tabela hash em memória `TRANSITIONS` é um dicionário Python com busca esperada O(1) para selecionar a transição por tipo de evento. As buscas persistidas usam chaves indexadas no SQLite. O registro do lote, o incremento de saldo e a auditoria são feitos na mesma transação SQL. Uma falha no insert de auditoria reverte as alterações anteriores. O saldo mede envelopes confirmados, pois o sensor identifica a presença de envelope.

```bash
python -m unittest discover -s tests -v
```

Resultado de 09/11/2026: 14 testes passaram (11 preservados e 3 da Sprint 3). Os testes novos cobrem validação, repetição, conflito, persistência após reinício e rollback forçado. Veja [a execução](evidencias/testes_entregas_2_3.txt).

[Validação por HTTP local](evidencias/http_sprint3.json) com um cliente Python que reproduz o JSON do ESP32.
