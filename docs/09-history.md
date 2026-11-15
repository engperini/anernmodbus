# 09 — Investigation history

## 11/11 — Battery bank and first steps
- Bank sizing: two 24 V LiFePO4 batteries (100 Ah each) in parallel, 1 m to the inverter. The nameplate confirmed a max. battery current of 175 A.
- Decision: parallel with the original cables + 2 cables of 50/70 mm² in diagonal to the inverter; protection by the built-in breakers.
- Solar Plug RWB1 dongle identified in the Sun house app. Goal: get the data into Home Assistant without the cloud.

## 11/12 — Reverse engineering
- Phone traffic capture (PCAPdroid): only TLS phone → cloud (`solar.siseli.com`); the cloud → dongle command does not go through the phone.
- Local BLE bridge created by the agent (Hermes) on the Raspberry Pi: Modbus read from slave 5 with valid CRC.
- LED search (prog 39): ON/OFF comparison over 5001–5038 and 4522–4541 with no result. 5036 (the LED on another model) did not change.
- APK analysis: `/near/dtu/...` routes; after logging in, the device protocol was downloaded: 6 FC03 frames, no write frames; attribute `rgbOnAndOffControlSetting` with no address.
- Discovered that **4561 is the LED state** (1 on, 0 off).
- Writing 4561 and 5042 with FC06 → `05 86 82` (refused). FC10 → `05 90 81` (not supported).
- Aligning the sequences 4541–4553 ↔ 5022–5034: **+481 offset** discovered by the agent.
- Public PowMr map found: confirms +481 and FC06. **Lesson: first look for what is already documented for the protocol pattern (slave 5, register 4501), only then test.**

## 11/13 — Validation and dashboard
- 00:10 — no-op write to 5018 (current value) → identical echo: write path validated.
- Labels corrected using the map (4542 = output voltage, 4544/4545 = back to grid/battery, 4548 = cut-off, 4549 = equalization).
- Programs 01 and 16 checked on the display: the PowMr numbering does **not** apply to the Anern texts. Actual mapping measured: 16 → CSO 0, SNU 1, OSO 2 (tested from HA).
- Original manual photographed: programs, fault/warning codes, BMS screens.
- Another agent's history: prog 43 = 48 with the BMS working; bP = battery not connected (the agent had called it bypass).
- Dashboard with locks, Groups A/B/C, fault/warning codes as text.
- 01:09 — **undervoltage and corrupted journal on the Pi**. From then on nothing else was written permanently (discovered only on 11/14).

## 11/14 — Losses and refinement
- 00:37 — Pi reboot: the dashboard went back to the 11/13 00:10 version. Rebuilt from the specification.
- 4501 = operating mode (3 battery, 4 bypass). 4535 and 4553 decoded with swapped bytes. 4512/4513 confirmed by the app and by Solar2MQTT.
- Dump compared with the Sun house app (Data details): CPU version, ratings, dual output cut-off in V and %, NTC.
- BMS screens on the display: firmware differs from the manual on screens 2 and 3; BMS data is outside the Modbus block.
- USB = 0 confirmed; total current 70 A written from HA.
- Second battery installed.
- ~13:20 — another power outage and reboot: everything went back to 11/13 again. Commits `438a250` and `7872e68` no longer exist on disk.
- Diagnosis: the SD card stopped persisting writes after the undervoltage of 11/13 01:09 (see `11-data-loss-incident.md`).
- This dossier was assembled from the conversation to preserve all the knowledge.

## Lessons
1. Look for the family's public maps before testing writes.
2. Always test a write with the current value first (no-op).
3. Check enum texts on the display: a family sibling's numbering may differ.
4. Persistence only counts after a real reboot of the Pi.
5. Keep a copy off the Pi (remote git) at every step.
6. A Pi exposed to power outages needs a UPS; without one, the SD card gets corrupted.
