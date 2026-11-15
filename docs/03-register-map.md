# 03 — Register map

Slave 5. Read FC03. Write FC06 at (read + 481). Values from the dump of 11/14/2026 11:27 (output SBU, charger OSO, charging from solar).
CSV version: [`data/registradores-4501-4564.csv`](../data/registradores-4501-4564.csv).

Status: ✅ confirmed (display, app or test) · 🟡 probable · ❓ unknown

## Telemetry and information

| Reg. | Dump | Field | Scale | Status |
|---|---|---|---|---|
| 4501 | 4 | Operating mode (see below) | enum | 🟡 3 and 4 confirmed |
| 4502 | 2178 | Grid voltage | ÷10 V | ✅ |
| 4503 | 600 | Grid frequency | ÷10 Hz | ✅ |
| 4504 | 1617 | PV voltage | ÷10 V | ✅ |
| 4505 | 253 | PV power | W | ✅ |
| 4506 | 267 | Battery voltage | ÷10 V | ✅ |
| 4507 | 34 | Battery SOC (from BMS) | % | ✅ |
| 4508 | 7 | Battery charge current | A | ✅ (= display) |
| 4509 | 0 | Battery discharge current | A | ✅ |
| 4510 | 2178 | Output voltage | ÷10 V | ✅ |
| 4511 | 600 | Output frequency | ÷10 Hz | ✅ |
| 4512 | 348 | Output apparent power | VA | ✅ |
| 4513 | 248 | Output active power | W | ✅ |
| 4514 | 8 | Load percentage | % | ✅ |
| 4515 | 8 | copy of load percentage? | % | 🟡 |
| 4516 | 0 | — | | ❓ |
| 4517 | 220 | Dual output cut-off (prog 42), in V | ÷10 V | ✅ |
| 4518 | 7511 | CPU version ("U1 75 11") | | ✅ |
| 4519 | 0 | — (candidate prog 37/41) | | ❓ |
| 4520 | 1 | — (candidate prog 44) | | ❓ |
| 4521 | 4200 | Rated power | W | ✅ |
| 4522 | 4200 | Rated power | VA | ✅ |
| 4523 | 230 | Rated AC voltage | V | ✅ |
| 4524 | 18 | Rated AC current | A | ✅ |
| 4525 | 240 | Rated battery voltage | ÷10 V | ✅ |
| 4526 | 230 | Rated output voltage | V | ✅ |
| 4527 | 500 | Rated frequency | ÷10 Hz | ✅ |
| 4528 | 18 | Rated output current | A | ✅ |
| 4529 | 0 | Warning code | enum | 🟡 |
| 4530 | 0 | Fault code | enum | ✅ |
| 4531–4533 | 5535 | unused (probably 65535) | | 🟡 |
| 4534 | 55 | Dual output cut-off (prog 42), in % | % | ✅ |
| 4535 | 292 | Configuration flags (swapped bytes) | bitmask | ✅ |
| 4553 | 5478 | Status flags (swapped bytes) | bitmask | 🟡 |
| 4554 | 2 | prog 38 (2 A) **or** battery state (2 = charging) | | ❓ |
| 4555 | 11 | — (10 on 11/13; not a current nor cycles) | | ❓ |
| 4556 | 11 | — (same as 4555) | | ❓ |
| 4557 | 40 | Max. NTC temperature | °C | ✅ |
| 4558–4559 | 0 | — | | ❓ |
| 4560 | 1 | — (candidate prog 44) | | ❓ |
| 4561 | 0 | Decorative LED state (prog 39): 0 LOF, 1 LON | | ✅ read-only |
| 4562–4564 | 0 | — | | ❓ |

### 4501 — Operating mode

| Code | Mode | Status |
|---|---|---|
| 0 | Power on | family |
| 1 | Standby (no output, can still charge from PV/mains; manual 5.6) | family |
| 2 | Line (grid) | family |
| 3 | **Battery mode** (battery and/or solar supply the loads; the vendor app calls it "Invert Mode") | ✅ observed |
| 4 | **Line mode / bypass** (mains supplies the loads and can charge; e.g. SBU with low battery, or USB) | ✅ observed |
| 5 | Charging | family |
| 6 | Fault | family |

"Family" = table from the sibling ISolar SMG/Anenji inverters (Solar2MQTT). Manual section 5.6
(`images/04-manual/manual-operating-modes-*.jpg`) lists Standby, Line, Grid-Tie and Battery modes;
codes 0, 1, 2, 5 and 6 and the code of Grid-Tie mode are still to be observed.

### 4535 — Configuration flags (swap the bytes first)

| Bit (after swap) | Setting | Prog | Write | On 11/14 |
|---|---|---|---|---|
| 0x0001 | Fault record | 25 | 5010 | on |
| 0x0002 | Battery equalization | 30 | — | off |
| 0x0004 | Immediate equalization | 36 | — | off |
| 0x0100 | Alarm | 18 | 5002 | off |
| 0x0400 | Backlight | 20 | 5004 | on |
| 0x0800 | Restart after overload | 06 | 5005 | off |
| 0x1000 | Restart after over-temperature | 07 | 5006 | off |
| 0x2000 | Beep on primary source failure | 22 | 5007 | on |
| 0x4000 | Return to default screen | 19 | 5008 | off |
| 0x8000 | Bypass on overload | 23 | 5009 | off |

Validation: matches 8/8 against 5002–5010 read directly, and the app shows "Battery equalization: off" and "Start balancing immediately: disable".

### 4553 — Status flags (swap the bytes first) 🟡

| Bit (after swap) | Meaning |
|---|---|
| 0x0100 | On battery |
| 0x0200 | Grid active |
| 0x1000 | Load off |
| 0x2000 | Grid active |
| 0x4000 | Load enabled |

Reading of 11/14 (0x6615): load enabled + grid active, "on battery" off, consistent with bypass. Confirm with the house on battery.

## Settings (read → write)

| Read | Write | Program | Values | Write status |
|---|---|---|---|---|
| 4536 | 5017 | 16 Charger priority | CSO=0 SNU=1 OSO=2 | ✅ 0, 1, 2 tested |
| 4537 | 5018 | 01 Output priority | USB=0 SUB=1 SBU=2 MKS=3 | ✅ 0, 1, 2 tested |
| 4538 | 5019 | 03 AC input range | APL=0 (90–280 V) UPS=1 (170–280 V) | not tested |
| 4539 | 5020 | 05 Battery type | AGM=0 FLD=1 USE=2 LIB=3 LIC=4 LIP=5 LIL=6 | not tested |
| 4540 | 5021 | 09 Output frequency | 50 Hz=0 60 Hz=1 | not tested |
| 4541 | 5022 | 02 Max. total charge current | A | ✅ tested |
| 4542 | 5023 | 10 Output voltage | 220/230/240 V | not tested |
| 4543 | 5024 | 11 Max. grid charge current | A | not tested |
| 4544 | 5025 | 12 Back to grid (SBU) | ÷10 V | not tested |
| 4545 | 5026 | 13 Back to battery (SBU) | ÷10 V | not tested |
| 4546 | 5027 | 26 Bulk voltage | ÷10 V | not tested |
| 4547 | 5028 | 27 Float voltage | ÷10 V | not tested |
| 4548 | 5029 | 29 Low battery cut-off | ÷10 V | not tested |
| 4549 | 5030 | 31 Equalization voltage | ÷10 V | not tested |
| 4550 | 5031 | 33 Equalization time | min | not tested |
| 4551 | 5032 | 34 Equalization timeout | min | not tested |
| 4552 | 5033 | 35 Equalization interval | days | not tested |
| bit 4535 | 5002, 5004–5010 | 18, 20, 06, 07, 22, 19, 23, 25 | 0/1 | state verified |

Addresses that **refuse** writes: 4561, 5042 (LED). 5003 was never identified.

## 50xx mirror (read, 2026-11-15 scan)

FC03 works on **5001–5038** (5039+ refused). The words come with the **bytes swapped**
relative to 45xx (e.g. 5022 = 0x5000 → 0x0050 = 80 A, 5025 = 0xF500 → 0x00F5 = 24.5 V):

| Range | Content |
|---|---|
| 5002, 5004–5010 | Group D settings as 0/1 (same as the 4535 bits) |
| 5017–5033 | mirror of 4536–4552 (the write registers read back) |
| 5034–5038 | mirror of 4553–4557 (status flags, 4554, 4555, 4556, NTC) |
| 5001, 5003, 5011–5016 | unknown, 0 |

Ranges that do not exist (exception `05 83 82`): 4001–4100, 4401–4500, 4565–4700, 5039–5100.
Raw results in `data/scan-2026-11-15-*.csv`; tool: `bridge/tools/scan_registers.py` (read-only).
