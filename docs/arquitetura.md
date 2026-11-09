# Arquitetura em blocos

```mermaid
flowchart TD
  H["Hardware · ESP32 e MicroPython"]
  A["API · FastAPI e validação JSON"]
  D[("BD relacional · SQLite")]
  S["Dashboard · Streamlit previsto na Parcial 4"]
  H -->|Wi-Fi e POST /events| A
  A -->|Transação SQL| D
  A -.->|Consulta futura| S
```

O firmware lê o HC-SR04 e os botões, sinaliza com LEDs e mantém uma pilha LIFO e uma fila de envio em RAM. Na Parcial 2, o destino é o servidor de teste em `server/app.py` com registro JSONL. Na Parcial 3, o destino usa a mesma rota POST com FastAPI e persistência relacional. O dashboard é uma etapa futura.
