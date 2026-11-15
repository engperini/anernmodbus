# Image index

Metadata (EXIF/GPS) removed. Images showing the dongle's serial number were removed from the public version.

## 01-hardware
- `etiqueta-inversor-an-sci-eco-4200.jpg` — full inverter nameplate (PV, output, AC input, battery 175 A).
- `dongle-rwb1-manual.jpg` — Solar Plug RWB1 dongle leaflet.

## 02-app-sunhouse
- `app-settings-2026-11-15-1…5.jpg` — every settings menu of the cloud app (Inverter, Equalization, System, Grid, Load), used for docs/10.
- `app-data-details-2026-11-15-1…6.jpg` — the app readings on 2026-11-15 11:08–11:23 (Invert Mode, grid/relay/PV/battery status texts).
- `app-led-pattern-switch.jpg` — "LED pattern switch" attribute (OFF/ON) in the app.
- `app-data-details-1…6.jpg` — the app's Data details screen on 11/14 10:13, used to map 4517, 4518, 4521–4528, 4557 and to confirm 4512/4513 and 4535.

## 03-protocolo-captura
- `pcapdroid-tls-app-nuvem.jpg` — phone capture: only TLS to the cloud; the command to the dongle does not go through the phone.

## 04-manual
- `manual-tabela-programas-1…5.jpg` — program table 00–45.
- `manual-bms-rj45-prog05-43.jpg` — BMS RJ45 cable, prog 05 (LIB-485) and 43 (protocol).
- `manual-telas-bms-p12.jpg`, `manual-telas-bms-foto2.jpg` — BMS screens according to the manual.
- `manual-codigos-alarme-bateria-p13.jpg`, `manual-codigos-falha-bateria-p14.jpg` — battery codes.
- `manual-codigos-falha-aviso-inversor-p33.jpg` — inverter fault (5.9) and warning (5.10) codes.
- `manual-troubleshooting.jpg` — troubleshooting table.
- `manual-operating-modes-p29.jpg`, `manual-operating-modes-battery-p30.jpg` — section 5.6, operating modes (Standby, Line, Grid-Tie, Battery) and their LCD screens.
- `manual-rgb-light-equalization.jpg` — RGB light colours per mode (battery red, utility blue, PV purple) and section 5.7, battery equalization (enable program 30, then 35 interval or 36 now).

## 05-display-inversor
- `display-39-LON.jpg` — program 39 (LED) on.
- `bms-tela1-tensao-soc.jpg` — 26.6 V / 39%.
- `bms-tela2-corrente-910.jpg` — 0 A / 910 (meaning unknown).
- `bms-tela3-24V-ciclos6.jpg` — 24.0 V / 6 cycles.
- `bms-tela-celulas-3v33-3v31.jpg` — cell max./min. voltage.
- `bms-tela-temp-25-29.jpg`, `bms-tela-temp-26-26.jpg` — MOS/cell temperatures.

## 06-dashboard-ha (dashboard evolution)
- `v1-13nov-*` — first version (provisional labels, numeric codes).
- `v1b-13nov-1017-*` — with open items and 4512/4513 confirmation.
- `v2-13nov-1240-*`, `v2-13nov-1343-*` — locks, Groups A/B/C, fault/warning as text.
- `v3-14nov-1004-*` — rebuild after the 1st loss (corrected names, tables).
- `v4-14nov-1113-*` — Group D, equalization binary sensors, open items.
- `v5-final-14nov-1225-*` — **final version** (Group B "parameters", USB tested, dual output cut-off, equipment information).

## 07-incidente
- `13nov-0353-ponte-ble-unavailable.jpg` — BLE bridge went down (everything Unavailable).
- `14nov-0155-reconstrucao-*` — dashboard during the rebuild after the 1st loss.
- `14nov-1400-ha-voltou-versao-antiga.jpg` — after the 2nd power outage, HA went back to the 11/13 state.
- `hermes-relatorio-*` — agent reports: rebuild, commits and the search that did not find the commits on disk.
