# Dossiê — Inversor Anern AN-SCI-ECO-4200 + Home Assistant (BLE → MQTT)

Registro completo da engenharia reversa e da integração local do inversor **Anern AN-SCI-ECO-4200 (4,2 kW / 24 V)** com o **Home Assistant**, feita entre 11 e 14/11/2026. Lendo e escrevendo parâmetros pelo dongle **Solar Plug RWB1** via Bluetooth (BLE), sem depender da nuvem do fabricante.

> Objetivo deste repositório: **não perder o conhecimento**. Tudo o que foi descoberto, confirmado e testado está aqui, com as evidências (prints do app, do display, do manual e do painel). Com este dossiê é possível reconstruir a ponte e o painel do zero.

> Repositório público: não há senhas, tokens, números de série do dongle nem endereços de rede aqui, e as fotos estão sem metadados (EXIF/GPS).

---

## Resumo do que funciona

| Item | Situação |
|---|---|
| Leitura de telemetria (FV, bateria, rede, saída, SOC do BMS) | ✅ confirmada |
| Escrita de parâmetros (FC06, endereço = leitura + 481) | ✅ confirmada em 5017, 5018 e 5022 |
| Prioridade do carregador (CSO/SNU/OSO) pelo HA | ✅ testada com mudança real |
| Prioridade de saída (USB/SUB/SBU) pelo HA | ✅ testada com mudança real |
| Corrente máx. de carga (prog 02) pelo HA | ✅ testada (40 → 70 A) |
| Flags de configuração (alarme, luz de fundo etc.) | ✅ decodificadas (bytes invertidos) |
| Códigos de falha e aviso | ✅ tabela completa do manual |
| Comunicação com o BMS (modo LIL, prog 43 = 48) | ✅ funcionando |
| LED decorativo (prog 39) | ⚠️ estado lido; endereço de escrita desconhecido |
| Dados detalhados do BMS (células, ciclos) | ❌ não estão no bloco Modbus |

## Índice

| Documento | Conteúdo |
|---|---|
| [docs/01-hardware.md](docs/01-hardware.md) | Inversor, etiqueta, baterias, ligação do banco, dongle, Raspberry Pi |
| [docs/02-protocolo.md](docs/02-protocolo.md) | Transporte BLE, Modbus, leitura/escrita, erros, CRC, bytes invertidos |
| [docs/03-mapa-registradores.md](docs/03-mapa-registradores.md) | **Mapa completo 4501–4564 e 5002–5033** |
| [docs/04-programas-display.md](docs/04-programas-display.md) | Programas 01–45 do display, valores e códigos |
| [docs/05-codigos-falha-aviso.md](docs/05-codigos-falha-aviso.md) | Códigos de falha/aviso do inversor e da bateria |
| [docs/06-bms.md](docs/06-bms.md) | Telas do BMS no display, diferenças de firmware, saúde da bateria |
| [docs/07-home-assistant.md](docs/07-home-assistant.md) | **Especificação completa do painel e dos controles** |
| [docs/08-ponte-ble.md](docs/08-ponte-ble.md) | Ponte BLE → MQTT: origem do código, requisitos, resiliência |
| [bridge/](bridge/) | **Código da ponte** (versão de 13/11 recuperada) |
| [docs/09-historico.md](docs/09-historico.md) | Linha do tempo da investigação e lições |
| [docs/10-pendencias.md](docs/10-pendencias.md) | O que ainda está em aberto e como resolver |
| [docs/11-incidente-perda-dados.md](docs/11-incidente-perda-dados.md) | Perda de dados por queda de energia / cartão SD e prevenção |
| [docs/12-reconstrucao.md](docs/12-reconstrucao.md) | **Passo a passo para reconstruir tudo** (inclui instrução pronta para agente) |
| [data/registradores-4501-4564.csv](data/registradores-4501-4564.csv) | Mapa em CSV (para código) |
| [data/dump-2026-11-14-1127.csv](data/dump-2026-11-14-1127.csv) | Dump bruto de referência |
| [images/INDEX.md](images/INDEX.md) | Índice das imagens/evidências |
| [raw/](raw/) | Relatórios originais dos agentes (texto) |

## Atalhos técnicos

- **Modbus:** escravo `5`, leitura `FC03` no bloco `4501–4564`, escrita **somente** `FC06` em `5002–5033`.
- **Endereço de escrita = endereço de leitura + 481** (ex.: lê 4537 → escreve 5018).
- **Erros:** `05 86 82` = FC06 em endereço inválido; `05 90 81` = FC10 não suportada; `05 03 82` = leitura em endereço inválido.
- **Bytes invertidos:** registradores de bitmask `4535` e `4553`.
- **Família:** mesmo protocolo dos PowMr HVM (mapas públicos: odya/esphome-powmr-hybrid-inverter, leodesigner/powmr_comm, softwarecrash/Solar2MQTT).

## Créditos e referências

- [odya/esphome-powmr-hybrid-inverter](https://github.com/odya/esphome-powmr-hybrid-inverter) — mapa de registradores PowMr
- [leodesigner/powmr_comm](https://github.com/leodesigner/powmr_comm) — quadros reais de escrita FC06
- [softwarecrash/Solar2MQTT](https://github.com/softwarecrash/Solar2MQTT) — confirmação de 4512/4513, tipos de bateria e modos de operação da família
- Manual impresso do Anern AN-SCI-ECO-4200 (fotos em `images/04-manual`)
