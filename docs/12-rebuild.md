# 12 — Rebuild

## Order

1. **Power:** official 27 W supply + UPS.
2. **Storage:** new card or SSD; install Raspberry Pi OS 64-bit.
3. **Copy from the old card** (read-only, on another computer or USB reader): `/home/pi/solar-rwb1-ble/` (11/13 bridge, with the BLE details) and `/home/pi/.homeassistant/` (configuration).
4. Install Home Assistant, Mosquitto and the bridge; systemd service.
5. Create a private git repository for HA + bridge, with a remote (`git push`).
6. Persistence test: test file + real reboot.
7. Rebuild the dashboard with the instruction below (or manually with `07-home-assistant.md`).
8. First use of each write: current value (echo) → real change → check on the display.

## Ready-made instruction for an agent (Hermes or another)

```
Rebuild the Anern AN-SCI-ECO-4200 inverter integration in Home Assistant using this repository's dossier as the single source (docs/02, 03, 05, 07, 08). Do not write anything to the inverter; I test the writes.

1) BLE → MQTT bridge: start from the 11/13 bridge (BLE and CRC working). Implement the map from docs/03 (swapped bytes in 4535 and 4553), discovery with retain + re-send on homeassistant/status=online, availability, reconnection with backoff, Bluetooth reset after repeated failures and the safe FC06 write flow (read → validate → write → echo → re-read; refusal = do not retry; log to the "Last setting result" sensor). Only write with the HA locks on.
2) Dashboard: exactly as in docs/07 (locks, Groups A–D, read-only cards in the order given, fault/warning codes as text from docs/05, alerts, open items from docs/10, precision, names with program number).
3) Persistence: dashboard in YAML at the path HA loads; everything in git with a push to the remote at every step; sync; proof with a REAL reboot of the Pi (sudo reboot) comparing SHA-256 before and after.
4) Send me screenshots of each card and the list of entities.
```
