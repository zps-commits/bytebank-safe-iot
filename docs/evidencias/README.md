# Evidências — 05/11/2026

- 01_diagrama_wokwi.png: circuito digital salvo, com todos os componentes.
- 02_push_push_wokwi.png: dois depósitos, pilha com dois lotes e LED verde aceso.
- 03_pop_confirmado_wokwi.png: POP do segundo, confirmação do primeiro e contagem zero.
- 04_sensor_5cm_wokwi.png e 05_sensor_rearmado_wokwi.png: HC-SR04 simulado em modo real de sensor, sem repetição enquanto próximo e com rearmamento.
- lifo_wokwi.txt e sensor_wokwi.txt: trechos reais do terminal visível; podem conter quebras de linha e sobreposição entre observações.
- 06_http_wokwi_tentativa.png e http_wokwi.txt: tentativa real no simulador com hostname local, sem recebimento comprovado, terminou em -202. Feita antes da guarda IPv4 final.
- api_pc.json: seis requisições HTTP reais originadas no PC, com data UTC e resposta.
- testes_pc.txt: saída da suíte de 11 testes; firmware usa periféricos substituídos no PC.

O circuito físico, foto/GIF, POST do ESP32 físico e credenciais de bancada não estão presentes nem foram simulados como evidência física. Os screenshots não são prova de bancada real. O endpoint final exige IPv4 e o Wokwi público é salvo com HTTP desligado.

## Parcial 4 — 19/11/2026

- `testes_sprint4.txt`: execução real de 19 testes no PC.
- `e2e_sprint4.json`: Streamlit AppTest → API HTTP real → ciclo de rede do firmware no PC → ACK → SQLite → painel; também verifica API indisponível.
- `servicos_sprint4.json`: inicialização da API, Streamlit e simulador de PC em processos separados.

GPIO e Wi-Fi físicos não foram acessados; a prova da integração completa na placa continua pendente. Não substituir vídeo de bancada por esses arquivos.
