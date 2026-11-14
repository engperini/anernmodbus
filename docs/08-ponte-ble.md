# 08 — Ponte BLE → MQTT

O código da ponte está em [`bridge/`](../bridge/) — **versão de 13/11/2026 recuperada** (ver `bridge/RECUPERACAO.md`):

- **Base pública:** [Jpedrotas/easun-rwb1-esphome](https://github.com/Jpedrotas/easun-rwb1-esphome) — protocolo BLE do dongle RWB1 (`tools/rwb1_ble_protocol.py`, `tools/ble_modbus_read.py`) e componente ESPHome.
- **Alterações do Hermes** reaplicadas a partir do histórico do agente: `bridge.py`, `settings_map.py`, testes, painel e serviço.
- Arquivos reconstruídos com o mesmo tamanho exato dos originais; 11 testes passando.

A versão final de 14/11 (motor de escrita com travas, decodificação de 4501/4535/4553, Grupos A–D) foi perdida e está especificada abaixo e em `07-home-assistant.md`.
## O que a ponte faz

1. Conecta por BLE ao dongle RWB1.
2. Lê periodicamente os quadros FC03 (ver `02-protocolo.md`), confere o CRC.
3. Decodifica os registradores (`03-mapa-registradores.md`) e publica no MQTT.
4. Publica o discovery do HA (sensores, selects, numbers, switches, buttons, binary_sensors).
5. Recebe comandos dos controles e executa o fluxo seguro de escrita FC06.

## Requisitos

- **Uma conexão BLE por vez**: pausar a ponte antes de usar o app em modo Bluetooth.
- Leituras em bloco não podem incluir endereços inválidos.
- **Resiliência:**
  - reconexão automática com recuo (backoff);
  - após N falhas seguidas, reiniciar só o adaptador Bluetooth (`bluetoothctl power off/on` ou reset HCI) e soltar conexões presas;
  - publicar `availability` no MQTT;
  - binary_sensor "Dados recentes (<5 min)" e alerta no HA se ficar sem dados.
- **Discovery:** `retain` + reenvio no birth message do HA (`homeassistant/status = online`).
- **Escrita:** ler → validar → FC06 → eco idêntico → reler → publicar o resultado em "Último resultado de ajuste"; respeitar as travas (`input_boolean`) do HA; nunca repetir após recusa.
- **Log** de cada escrita: data, parâmetro, valor antigo, novo, resultado.
- **Bytes invertidos** em 4535 e 4553.
- Serviço `systemd` com `Restart=always`, apontando para o caminho versionado em git.

## Testes que existiam

A versão final tinha 26 testes automatizados (decodificação, validação de faixas e regras, montagem de quadros e CRC) e passava no `check_config` do HA. Recriar ao menos: CRC, decodificação de cada registrador, troca de bytes, validação das regras do Grupo B e recusa de escrita sem trava.
