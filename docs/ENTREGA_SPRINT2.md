# Entrega Sprint 2 — ByteBank Safe

Validação: 05/11/2026. Projeto didático; não movimenta dinheiro.

Simulador salvo: https://wokwi.com/projects/479892016343212033

## O que está demonstrado

| Requisito | Resultado real | Prova |
|---|---|---|
| MicroPython, botões e LEDs | Testado em simulação | Capturas 01 a 03 |
| Pilha LIFO | PUSH A, PUSH B, POP B, confirmar A; contagens 1, 2, 1, 0 | `evidencias/lifo_wokwi.txt` |
| Ultrassônico | 200 → 5 → 400 → 5 → 400 cm; dois eventos, sem repetição enquanto próximo | Capturas 04 e 05; `sensor_wokwi.txt` |
| Wi-Fi | Rede virtual Wokwi-GUEST conectada, IP 10.10.0.2 | Terminal nas capturas |
| API HTTP | PC recebeu 200 saúde, 201 evento novo, 200 duplicado, 400 e 422 inválidos, 200 lista | `evidencias/api_pc.json` |
| Testes de regressão | Consulte resultado em `testes_pc.txt` | API e firmware no PC, com periféricos substituídos |
| POST realmente recebido de ESP32 | Não comprovado | Necessário ESP32 físico na LAN ou gateway apropriado |
| Foto/GIF físico | Pendente bancada | Precisa montagem real |
| Repositório público IoT | Pendente destino | Busca por ByteBank Safe não identificou repositório; ByteBank de terminal é projeto distinto |
| Classroom | Pendente envio humano | Revisar nomes, rubrica e anexos antes de enviar |

## Copiar para a placa física

1. Separe ESP32 clássico, cabo USB de dados, protoboard, jumpers, três botões, LEDs verde/vermelho, dois resistores de 330 Ω e HC-SR04. Separe ainda 1 kΩ e 2 kΩ para adaptar ECHO.
2. Desconecte USB durante a montagem. Una os GNDs. Cada botão liga um GPIO ao GND: envelope 27, cancelar 14, confirmar 15. Não segure GPIO15 ao ligar/reiniciar; confira o modelo da placa.
3. Ligue GPIO2 → 330 Ω → ânodo do LED verde; cátodo → GND. Repita GPIO4 para o vermelho. A posição física dos pinos depende da placa.
4. HC-SR04: VCC à alimentação de 5 V compatível, GND comum, TRIG ao GPIO5. **ECHO de 5 V nunca vai direto ao GPIO18 físico.** Ligue ECHO → 1 kΩ → nó GPIO18; do mesmo nó, 2 kΩ → GND. Confira tensão/tolerâncias ou use conversor de nível adequado. O fio direto do simulador é apenas digital.
5. Deixe relé/solenóide desconectados. GPIO23 fica reservado e inativo. Não ligue carga indutiva diretamente ao ESP32.
6. Confira polaridade, curtos e divisor antes de conectar USB. No Thonny, selecione MicroPython ESP32 e porta COM. Instale firmware adequado somente se necessário.
7. Copie `esp32/config.example.py` para `config.py`, preencha Wi-Fi local e `API_URL='http://IP-LAN-DO-PC:8000/events'`. Mantenha `HTTP_ENABLED=True`, `SIMULATE_ENVELOPE=True`, `ENABLE_RELAY=False`. Não publique esse `config.py`.
8. Salve `config.py`, `boot.py` e `main.py` na raiz da ESP32 pelo Thonny. No computador, entre na raiz do projeto e execute `python -m server.app`. Use a mesma rede local, sem isolamento, e firewall apenas de rede privada.
9. Reinicie a placa. Observe conexão no REPL; pressione envelope duas vezes, cancelar e confirmar. Aguarde até 5 s por tentativa de envio. Verifique quatro eventos em `http://localhost:8000/events`; registre HTTP 201/200 e os IDs, sem expor credenciais.
10. Desligue antes de ajustar fios. Ative `SIMULATE_ENVELOPE=False`, reinicie e teste objeto passando abaixo de 10 cm e saindo acima de 12 cm. Calibre para a montagem.
11. Tire foto real da bancada, print do REPL e dos eventos no servidor. Adicione os arquivos a `docs/evidencias/` e atualize os estados do README apenas com o que demonstrar.
12. Preencha integrantes, publique no repositório escolhido e envie o link no Classroom. O ZIP já contém README, código, pinagem, arquitetura e evidências da simulação/PC.

## Repetir a simulação

Abra o link salvo e inicie. O padrão é modo de botão, com HTTP desligado. Clique e segure o botão por pelo menos 35 ms; para testar pela interface, Ctrl+clique fixa o botão pressionado e o clique seguinte solta (Cmd no Mac). Solte entre ações. A fila continua em RAM mesmo com HTTP desabilitado e tem limite de 50 eventos. Reinicie para limpar uma demonstração sem servidor.

Para sensor, edite `SIMULATE_ENVELOPE=False`, reinicie, clique no HC-SR04 e ajuste o controle de distância. O primeiro cruzamento abaixo de 10 cm dispara; acima de 12 cm rearma. Os botões CANCELAR/CONFIRMAR continuam ativos.

## Limitações

Pilha/fila voláteis; HTTP síncrono; cliente restrito a IPv4 numérico para evitar DNS no loop; leituras podem ser perdidas durante envio. Boot tenta conectar por tempo limitado, e o loop tenta reconectar periodicamente, mas a reconexão após corte de rede não foi demonstrada no simulador. Não há banco SQL nem Streamlit nesta sprint. O JSONL é registro de testes. Idempotência por `event_id` é básica e pode ter colisão após reboot. Sensor não infere valor financeiro. Confirmação é local e não garante recebimento do evento pelo servidor.


### DNS e endpoint desta revisão

A tentativa real no Wokwi com `host.wokwi.internal` ficou bloqueada na resolução/conexão e só depois registrou `Servidor indisponível (evento preservado): -202`. Para evitar DNS no loop, o cliente final valida um IPv4 numérico em URL HTTP e mantém o evento na fila quando a configuração usa hostname. Na bancada use `http://IP-LAN-DO-PC:8000/events`. O endereço antigo do Wokwi é apenas marcador: com `HTTP_ENABLED=False` não é usado. Habilitá-lo com esse hostname agora produz erro local explícito, sem efetuar POST. A requisição síncrona ao IPv4 continua sujeita ao timeout de socket de 2 segundos e pode atrasar leituras. HTTPS e hostnames exigem projeto de rede posterior.
