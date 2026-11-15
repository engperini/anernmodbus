# Anern AN-SCI-ECO-4200 inverter → Home Assistant (local Bluetooth, no cloud)

Read **and** change the settings of an **Anern AN-SCI-ECO-4200** hybrid solar inverter
(4.2 kW / 24 V) from **Home Assistant**, through the **Solar Plug RWB1** Bluetooth dongle
that ships with it. A small Python bridge running on a Raspberry Pi (or any Linux box with
Bluetooth) talks to the dongle over BLE and publishes everything to MQTT, with Home
Assistant auto-discovery.

```
inverter ── RWB1 dongle ──BLE── Raspberry Pi (bridge.py) ──MQTT── Home Assistant
```

> Unofficial community project, not affiliated with Anern, the RWB1 maker or the vendor app.
> Changing inverter settings is your responsibility: read the inverter and battery manuals first.

## What you get

- **Telemetry**: PV voltage/power, battery voltage/SOC (from the BMS)/currents, grid, output,
  load, NTC temperature, operation mode, fault and warning **as text**.
- **Controls** (MQTT select / number / switch / button), grouped like the inverter programs:
  - **Group A** · charger source (16), output source (01)
  - **Group B** · charge currents, back to grid/battery, bulk, float, cutoff, equalization
  - **Group C** · AC input range, battery type, output frequency, output voltage
    (needs two locks and a confirmation)
  - **Group D** · alarm, backlight, auto-restart, beep, bypass, fault record
- **Safe writes**: every change is validated (range, step, cross-rules), written once with
  Modbus FC06, the echo is checked, the value is read back and the result is shown in
  "Last setting result". A refusal is never retried. Writes only happen while the
  **edit locks** in Home Assistant are on; they turn off by themselves after 10 minutes.
- **Alerts**: inverter fault, BMS communication lost (code 61), warning for more than 2 min,
  bridge without data for 5 min.
- A ready **dashboard** (`homeassistant/anern_dashboard.yaml`).

| Feature | Status |
|---|---|
| Telemetry (PV, battery, grid, output, BMS SOC) | ✅ confirmed |
| Writes (FC06, address = read register + 481) | ✅ tested on 5017, 5018, 5022 |
| Configuration flags (alarm, backlight…) | ✅ decoded |
| Fault and warning codes | ✅ full table from the manual |
| Decorative LED (program 39) | ⚠️ state only, write address unknown |
| Detailed BMS data (cells, cycles) | ❌ not in the Modbus block |

## Project status

Complete and in daily use. Compared with the vendor cloud app, everything is covered except
the writes of programs 30, 36, 37, 38, 39, 41 and 42 (see [docs/10](docs/10-open-items.md)).

## Installation

You need:
- the inverter with its **RWB1** dongle, and the dongle's **DTU ID** (see below);
- a **Raspberry Pi** (any model with Bluetooth; tested on a Pi 5 with Raspberry Pi OS
  Bookworm and Trixie) within Bluetooth range of the dongle;
- an **MQTT broker** that Home Assistant uses (the Mosquitto add-on on HA OS, or
  Mosquitto on the Pi itself).

Only one Bluetooth connection to the dongle works at a time: close the vendor app on your
phone (or switch it to cloud mode) while the bridge runs.

### 1. Find the DTU ID

Open the vendor app → your installation → **Device Information**, and copy the row called
**DTU ID**, **Device PN** or **Device Name** (a long number). It is **not** the SN row, not
the `SSL_...` Bluetooth name and not a MAC address. The bridge uses it locally to derive the
dongle's encryption key; keep it private.

### 2. Install the bridge on the Raspberry Pi

```bash
sudo apt install -y git
git clone https://github.com/engperini/anernmodbus.git
cd anernmodbus/bridge
./install.sh
```

The installer asks for the DTU ID and the MQTT broker, then:
1. installs what is missing (`python3-venv`, `bluez`);
2. creates a Python virtual environment with the dependencies;
3. writes `rwb1.env` (your settings, mode 600, never committed);
4. finds the dongle by Bluetooth (it advertises as `SSL_...`);
5. runs the unit tests and one test read;
6. installs a **systemd user service** (`rwb1-ble`) and enables *lingering*, so the bridge
   starts at every boot and restarts by itself if it stops.

Non-interactive example (broker = Mosquitto add-on of Home Assistant OS):

```bash
./install.sh --dtu-id 12345678901234567890 \
  --mqtt-host 192.168.1.10 --mqtt-user mqtt_user --mqtt-password 'your-password'
```

Useful commands:

```bash
journalctl --user -u rwb1-ble -f        # live log
systemctl --user restart rwb1-ble       # restart
.venv/bin/python bridge.py --scan       # list nearby RWB1 dongles
.venv/bin/python bridge.py --once       # one read, print the result, exit
./install.sh --uninstall                # remove the service
```

To change a setting later (broker, interval…), run `./install.sh` again with the new
option, or edit `rwb1.env` and restart the service.

### 3. Home Assistant

1. **MQTT integration**: Settings → Devices & services → MQTT, pointing to the same broker.
   The device **"Anern solar inverter"** appears by itself (MQTT discovery).
2. **Package** (locks, alerts, "data fresh" sensor): copy
   [`homeassistant/anern_package.yaml`](homeassistant/anern_package.yaml) to
   `<config>/packages/anern.yaml` and enable packages in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. **Dashboard**: copy
   [`homeassistant/anern_dashboard.yaml`](homeassistant/anern_dashboard.yaml)
   to your config folder and register it in `configuration.yaml`:
   ```yaml
   lovelace:
     dashboards:
       anern-inverter:
         mode: yaml
         title: Anern inverter
         icon: mdi:solar-power
         show_in_sidebar: true
         filename: anern_dashboard.yaml
   ```
4. Restart Home Assistant (Developer tools → Check configuration first).

On **Home Assistant OS** use the *File editor* or *Samba share* add-on to copy the files.
On **HA Core** in the same Pi you can link them instead of copying, so `git pull` updates
them: `ln -s ~/anernmodbus/homeassistant/anern_package.yaml <config>/packages/anern.yaml`.

### 4. First write

Writes for many programs were never tested on this inverter. For each control, the first
time: turn on **Edit mode**, write the **current** value (echo test), check "Last setting
result", then make the real change and confirm it on the inverter display. Group C also
needs **Critical settings** and the **Apply** button.

## How it works

| Item | Value |
|---|---|
| BLE | service `FEE7`, write `FED5`, indicate `FED6`; encrypted, fragmented frames |
| Modbus | slave `5`; read `FC03` block `4501–4564` (64 registers, one request) |
| Writes | **only** `FC06`, register = read register **+ 481** (e.g. read 4537 → write 5018) |
| Errors | `05 86 82` FC06 refused · `05 90 81` FC10 unsupported · `05 03 82` invalid read |
| Byte order | words little-endian; bitmasks `4535` and `4553` have swapped bytes |
| Family | same protocol as the PowMr HVM series |

MQTT topics: `solar/rwb1_ble/<id>/state` (JSON, retained), `/availability`,
`/set/<key>`, `/apply/<key>`, `/result`, and `solar/rwb1_ble/locks` (from the HA package).
Details in [docs/08-ble-bridge.md](docs/08-ble-bridge.md).

## Documentation

| Document | Content |
|---|---|
| [docs/01-hardware.md](docs/01-hardware.md) | Inverter, label, batteries, dongle, Raspberry Pi |
| [docs/02-protocol.md](docs/02-protocol.md) | BLE transport, Modbus, reads/writes, errors, CRC, byte swap |
| [docs/03-register-map.md](docs/03-register-map.md) | **Full map 4501–4564 and 5002–5033** |
| [docs/04-display-programs.md](docs/04-display-programs.md) | Display programs 01–45, values and codes |
| [docs/05-fault-warning-codes.md](docs/05-fault-warning-codes.md) | Inverter and battery fault/warning codes |
| [docs/06-bms.md](docs/06-bms.md) | BMS screens on the display, battery health |
| [docs/07-home-assistant.md](docs/07-home-assistant.md) | **Dashboard and controls specification** |
| [docs/08-ble-bridge.md](docs/08-ble-bridge.md) | The bridge: code, install, MQTT topics, resilience |
| [docs/09-history.md](docs/09-history.md) | Investigation timeline and lessons |
| [docs/10-open-items.md](docs/10-open-items.md) | What is still unknown and how to find out |
| [docs/11-data-loss-incident.md](docs/11-data-loss-incident.md) | SD card data loss after power cuts, and prevention |
| [docs/12-rebuild.md](docs/12-rebuild.md) | Step by step to rebuild everything |
| [data/](data/) | Register map in CSV and a raw reference dump |
| [images/INDEX.md](images/INDEX.md) | Screenshots and photos used as evidence |

## Credits

- [Jpedrotas/easun-rwb1-esphome](https://github.com/Jpedrotas/easun-rwb1-esphome) — RWB1 BLE
  protocol and key derivation (the base of `bridge/tools/`); its ESPHome component is kept in
  `bridge/` (see `bridge/README.md`)
- [odya/esphome-powmr-hybrid-inverter](https://github.com/odya/esphome-powmr-hybrid-inverter) — PowMr register map
- [leodesigner/powmr_comm](https://github.com/leodesigner/powmr_comm) — real FC06 write frames
- [softwarecrash/Solar2MQTT](https://github.com/softwarecrash/Solar2MQTT) — 4512/4513, battery types and operation modes of the family

No passwords, tokens, dongle serial numbers or network addresses are published here, and the
photos have no EXIF/GPS metadata.
