# BLE bridge recovery (11/14/2026)

The bridge files on the Raspberry Pi's SD card were zeroed out (content made only of null bytes) after the power outages of 11/13.
This folder was rebuilt as follows:

1. **Base:** public project [Jpedrotas/easun-rwb1-esphome](https://github.com/Jpedrotas/easun-rwb1-esphome) (license in `LICENSE`), which the Hermes agent cloned on 11/12 as its starting point. It contains the RWB1 BLE protocol (`tools/rwb1_ble_protocol.py`, `tools/ble_modbus_read.py`) and the ESPHome component.
2. **Hermes's changes:** reapplied in the original order from the agent's history (`~/.hermes/state.db`, up to 11/13 00:06): `bridge.py`, `settings_map.py`, `test_settings_map.py`, `fixtures/`, `docs/pending-selects.md`, dashboard (`homeassistant/`), service (`systemd/`) and research scripts (`tools/research/`).

Verification: the rebuilt files have exactly the same size in bytes as the zeroed files on the Pi (bridge.py 8139, settings_map.py 4462, test_settings_map.py 4935, settings_read.json 407, pending-selects.md 1695) and the 11 tests pass (`python3 -m unittest`).

State: version of 11/13 00:06 — BLE/Modbus reading with CRC, MQTT publishing, settings mapping and a no-op write test on 5018. It **does not include** the write engine with locks, the decoding of 4501/4535/4553 or the Group A–D controls of the final 11/14 version (lost; specified in `../docs/07-home-assistant.md` and `../docs/08-ble-bridge.md`). The bridge was later rebuilt on 11/15/2026 (`anern_map.py`, `bridge.py`, tests); see `../docs/08-ble-bridge.md`.

`rwb1.env` (dongle ID and BLE address) was replaced by `rwb1.env.example`.
The scripts in `tools/research/` use Pi paths (`/home/pi/.config/siseli/...`) and were kept as a record of the LED and register investigation.
