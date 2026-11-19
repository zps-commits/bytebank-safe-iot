# Wokwi validado em 05/11/2026

Projeto público: https://wokwi.com/projects/479892016343212033

Os arquivos desta pasta correspondem à revisão final. O padrão usa botões e `HTTP_ENABLED=False`. Houve execução real de PUSH, PUSH, POP e confirmação, conexão Wi-Fi virtual e leitura HC-SR04 alternando 200, 5, 400, 5 e 400 cm. Veja evidências no README principal e `docs/evidencias/`.

Clique e segure por mais de 35 ms, ou Ctrl+clique para fixar o botão e clique novamente para soltar (Cmd no Mac). Mantenha soltura entre dois depósitos. Para o sensor, mude `SIMULATE_ENVELOPE=False`, reinicie e ajuste a distância no HC-SR04. Dispara abaixo de 10 cm; rearma acima de 12 cm.

HTTP está desligado para demonstração. A fila permanece em RAM e limita a 50 eventos; reinicie a simulação para limpá-la quando não houver servidor. O hostname local legado ficou esperando e retornou -202 no teste. A revisão final rejeita hostnames antes de DNS, exige IPv4 numérico em API_URL e preserva o evento. O POST ao servidor da bancada ainda precisa ser demonstrado no ESP32 físico na mesma LAN. Não foi contratado nem configurado gateway privado.

ECHO direto ao GPIO18 só é válido no simulador digital. No HC-SR04 real alimentado em 5 V, use divisor ECHO → 1 kΩ → GPIO18 e GPIO18 → 2 kΩ → GND ou conversor adequado.

## Revisão Parcial 4

Os arquivos locais `main.py` e `command_state.py` incluem a rede em thread e o comando `reset_counter`. Copie também `command_state.py` ao criar uma simulação nova. O projeto público no link acima foi validado na Sprint 2 e não foi atualizado nem reexecutado nesta revisão. A configuração Wokwi mantém HTTP desligado; não comprova o caminho até a API local do computador. Para a prova end-to-end siga o guia físico da Parcial 4 ou o simulador de PC claramente identificado.
