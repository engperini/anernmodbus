# 08 — Ponte BLE → MQTT

O código da ponte (`/home/pi/solar-rwb1-ble/bridge.py`, `settings_map.py`, `control_engine`) foi perdido na versão final, mas **a versão de 13/11 (leitura com CRC válido, MQTT online) continua no Pi**. Comece por ela.

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
