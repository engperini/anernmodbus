# 01 — Hardware

## Inverter: Anern AN-SCI-ECO-4200

Nameplate data (photo: `images/01-hardware/etiqueta-inversor-an-sci-eco-4200.jpg`):

| Group | Parameter | Value |
|---|---|---|
| General | Model | AN-SCI-ECO-4200 |
| | Operating temperature | −10 to 50 °C |
| PV input | Rated voltage | 240 Vdc |
| | PV Vmax | 500 Vdc |
| | PV input range | 60–450 Vdc |
| | MPPT range at full load | 240–450 Vdc |
| | Max. PV current | 18 A |
| | Max. PV power | 6200 W |
| | Max. solar charge current | 120 A |
| AC output | Rated voltage | 220/230/240 Vac |
| | Rated current | 18.2 A |
| | Max. efficiency | 97% |
| | Frequency | 50/60 Hz |
| Dual output | Total / main load | 4200 W / 4200 W |
| | Second output max. | 1400 W (prog 45 = 33%) |
| | Main load cut-off / restore | 26 / 27 Vdc |
| AC input | Rated voltage | 230 Vac |
| | Max. input current | 30 A |
| | Surge | 8400 VA |
| | Max. AC charge current | 100 A |
| Battery | Voltage | 24 Vdc |
| | **Max. battery current** | **175 A** |

Main CPU firmware: **U1 75 11** (register 4518 = 7511).

Notes:
- The manual contradicts itself on the MPPT limit (450 V on p. 8, 500 V on p. 39). Go by the nameplate.
- The manual's spec table says 50 Hz; the unit runs at 60 Hz without issues (prog 09).
- Tested: the inverter starts and powers loads from PV alone, **with no battery** connected.

## Batteries

- **24 V lithium battery (LiFePO4 25.6 V / 100 Ah)**, BMS with RS485/CAN, built-in breaker and fuse.
- Recommended: 100 A continuous per battery, 150 A for 15 s. Max. charge 28.8 V, cut-off 24 V.
- Current setup: **two batteries in parallel**.
- BMS ↔ inverter communication **works** with prog 05 = LIL and prog 43 = 48 (see `06-bms.md`).

## Battery bank wiring (final decision)

Bank 1 m from the inverter, batteries side by side:

- Parallel link between the batteries using the battery maker's original cables (35 mm²): + to +, − to −.
- To the inverter: **2 cables of 50 mm² (or 70 mm²), 1 m, diagonal**: positive from one battery and negative from the other, to split the current evenly.
- 50 mm² lugs with the **same hole size** as the battery terminal (probably M8), crimped with a hydraulic crimper. Two lugs stacked on the post, metal to metal; washer only on top.
- Protection: the batteries' built-in breakers serve as disconnects. (A sturdier alternative, with a 300 A busbar, NH1 200 A gG fuse and NH1 fuse base, was evaluated and documented, but was not needed with the bank 1 m away.)
- Before adding a new battery: switch everything off and equalize the voltages (charge both to 100%).

Design current: 4200 W ÷ (24 V × 0.93) ≈ 188 A worst case; the inverter limits it to 175 A.

## Dongle: Solar Plug RWB1

- Siseli Wi-Fi/BLE datalogger, **Sun house** app (`com.ssli.next.solar`, v1.1.5).
- Firmware: **V1.44.5_SolarV70**, Type NO 04.
- Plugged into the inverter's communication port; sends data to the app's cloud and accepts a local BLE connection.
- **Accepts one BLE connection at a time**: the app in Bluetooth mode and the bridge cannot run simultaneously.
- Photos: `images/01-hardware/dongle-rwb1-*.jpg`.

## Server: Raspberry Pi 5

- Runs Home Assistant (config in `/home/pi/.homeassistant`), Mosquitto and the BLE bridge (`/home/pi/solar-rwb1-ble`).
- Built-in Bluetooth adapter.
- **Needs the official 27 W (5 V / 5 A) power supply** and, because of the frequent power outages, a **UPS**. See `11-data-loss-incident.md`.
