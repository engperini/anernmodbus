# Recuperação da ponte BLE (14/11/2026)

Os arquivos da ponte no cartão SD do Raspberry Pi ficaram zerados (conteúdo só com bytes nulos) depois das quedas de energia de 13/11.
Esta pasta foi reconstruída assim:

1. **Base:** projeto público [Jpedrotas/easun-rwb1-esphome](https://github.com/Jpedrotas/easun-rwb1-esphome) (licença em `LICENSE`), que o agente Hermes clonou em 12/11 como ponto de partida. Contém o protocolo BLE do RWB1 (`tools/rwb1_ble_protocol.py`, `tools/ble_modbus_read.py`) e o componente ESPHome.
2. **Alterações do Hermes:** reaplicadas na ordem original a partir do histórico do agente (`~/.hermes/state.db`, até 13/11 00:06): `bridge.py`, `settings_map.py`, `test_settings_map.py`, `fixtures/`, `docs/pending-selects.md`, painel (`homeassistant/`), serviço (`systemd/`) e scripts de pesquisa (`tools/research/`).

Verificação: os arquivos reconstruídos têm exatamente o mesmo tamanho em bytes dos arquivos zerados do Pi (bridge.py 8139, settings_map.py 4462, test_settings_map.py 4935, settings_read.json 407, pending-selects.md 1695) e os 11 testes passam (`python3 -m unittest`).

Estado: versão de 13/11 00:06 — leitura BLE/Modbus com CRC, publicação MQTT, mapeamento de ajustes e teste de escrita sem efeito em 5018. **Não inclui** o motor de escrita com travas, a decodificação de 4501/4535/4553 nem os controles dos Grupos A–D da versão final de 14/11 (perdidos; especificados em `../docs/07-home-assistant.md` e `../docs/08-ponte-ble.md`).

`rwb1.env` (ID do dongle e endereço BLE) foi substituído por `rwb1.env.example`.
Os scripts em `tools/research/` usam caminhos do Pi (`/home/pi/.config/siseli/...`) e foram mantidos como registro da investigação do LED e dos registradores.
