# 08 — BLE → MQTT bridge

The bridge code is in [`bridge/`](../bridge/). **Rebuilt on 11/15/2026** from this dossier, on top of the recovered 11/13 base (see `bridge/RECOVERY.md`):

- `bridge/anern_map.py`: map of 4501–4564 (a single FC03 of 64 registers), mode/fault/warning texts, byte swap for 4535/4553, Group A–D controls with ranges, steps and rules, FC06 frames.
- `bridge/bridge.py`: periodic polling, MQTT discovery (with `retain` and re-sent on `homeassistant/status = online`), safe writing with locks, reconnection with backoff, Bluetooth reset after 5 failures, write log in `bridge/writes.log`.
- `bridge/test_anern_map.py`: decoding with the 11/14 dump, frames from the doc 02 examples, ranges, rules and refusal to write without a lock.
- On Debian 13 (BlueZ/dbus-fast), `stop_notify`/`disconnect` can fail with `EOFError` after a good read; the bridge ignores this error on shutdown.

History:

- **Public base:** [Jpedrotas/easun-rwb1-esphome](https://github.com/Jpedrotas/easun-rwb1-esphome) — BLE protocol of the RWB1 dongle (`tools/rwb1_ble_protocol.py`, `tools/ble_modbus_read.py`) and ESPHome component.
- **Hermes's changes** reapplied from the agent's history: `bridge.py`, `settings_map.py`, tests, dashboard and service.
- Files rebuilt with exactly the same size as the originals; 11 tests passing.

The final 11/14 version (write engine with locks, decoding of 4501/4535/4553, Groups A–D) was lost; the 11/15 version reimplements it according to the specification below and `07-home-assistant.md`.

## Installation (Raspberry Pi)

Use the installer; it sets up the venv, `rwb1.env`, a test read and the persistent
systemd user service (with lingering, so it starts at boot):

```bash
cd bridge
./install.sh            # or: ./install.sh --dtu-id ... --mqtt-host ... --mqtt-user ... --mqtt-password ...
```

Full guide (including the Home Assistant part) in the [README](../README.md#installation).
`rwb1.env` keys: `RWB1_DTU_ID`, `RWB1_BLE_ADDRESS` (optional, found by scan),
`RWB1_INTERVAL`, `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD`.

## MQTT topics

| Topic | Use |
|---|---|
| `solar/rwb1_ble/<id>/state` | JSON with all values (retain) |
| `solar/rwb1_ble/<id>/availability` | `online` / `offline` |
| `solar/rwb1_ble/<id>/set/<key>` | command for a control (Group C only stages) |
| `solar/rwb1_ble/<id>/apply/<key>` | applies the staged Group C value |
| `solar/rwb1_ble/locks` | `{"edit": bool, "critical": bool}` published by the HA package |
| `solar/rwb1_ble/<id>/result` | text of the last setting change |

## What the bridge does

1. Connects over BLE to the RWB1 dongle.
2. Periodically reads the FC03 frames (see `02-protocol.md`) and checks the CRC.
3. Decodes the registers (`03-register-map.md`) and publishes to MQTT.
4. Publishes the HA discovery (sensors, selects, numbers, switches, buttons, binary_sensors).
5. Receives commands from the controls and runs the safe FC06 write flow.

## Requirements

- **One BLE connection at a time**: pause the bridge before using the app in Bluetooth mode.
- Block reads must not include invalid addresses.
- **Resilience:**
  - automatic reconnection with backoff;
  - after N consecutive failures, restart only the Bluetooth adapter (`bluetoothctl power off/on` or HCI reset) and release stuck connections;
  - publish `availability` to MQTT;
  - binary_sensor "Recent data (<5 min)" and an HA alert if data stops arriving.
- **Discovery:** `retain` + re-send on the HA birth message (`homeassistant/status = online`).
- **Writing:** read → validate → FC06 → identical echo → re-read → publish the result to "Last setting result"; honor the HA locks (`input_boolean`); never retry after a refusal.
- **Log** of every write: date, parameter, old value, new value, result.
- **Swapped bytes** in 4535 and 4553.
- `systemd` service with `Restart=always`, pointing to the git-versioned path.

## Tests that existed

The final version had 26 automated tests (decoding, range and rule validation, frame building and CRC) and passed HA's `check_config`. Recreate at least: CRC, decoding of each register, byte swap, validation of the Group B rules and refusal to write without a lock.
