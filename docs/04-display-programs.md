# 04 — Display programs

Inverter menu programs, with the values checked on the display on 11/13–14/2026. Where the manual and the unit disagree, the unit wins.

| Prog | Function | Options (display) | Current value | Register |
|---|---|---|---|---|
| 01 | Output priority | USB (grid first), SUB (solar first), SBU (solar → battery → grid), MKS | SBU / USB (tests) | 4537 / 5018 |
| 02 | Max. total charge current | 10–120 A | 40 → 70 A | 4541 / 5022 |
| 03 | AC input range | APL 90–280 V, UPS 170–280 V | UPS | 4538 / 5019 |
| 05 | Battery type | AGM, FLd, USE, LIB, LIC, LIP, LIL | LIL | 4539 / 5020 |
| 06 | Restart after overload | on/off | off | bit 0x0800 / 5005 |
| 07 | Restart after over-temperature | on/off | off | bit 0x1000 / 5006 |
| 09 | Output frequency | 50 / 60 Hz | 60 Hz | 4540 / 5021 |
| 10 | Output voltage | 220 / 230 / 240 V | 220 V | 4542 / 5023 |
| 11 | Max. grid charge current | 2, 10 … 100 A | 2 A | 4543 / 5024 |
| 12 | Back to grid (SBU) | V (or % with LIB-485) | 24.5 V | 4544 / 5025 |
| 13 | Back to battery (SBU) | V, FUL | 27.0 V | 4545 / 5026 |
| 16 | Charger priority | CSO, SNU, OSO | OSO | 4536 / 5017 |
| 18 | Alarm | on/off | off | bit 0x0100 / 5002 |
| 19 | Return to default screen | on/off | off | bit 0x4000 / 5008 |
| 20 | Backlight | on/off | on | bit 0x0400 / 5004 |
| 22 | Beep on primary source failure | on/off | on | bit 0x2000 / 5007 |
| 23 | Bypass on overload | on/off | off | bit 0x8000 / 5009 |
| 25 | Fault record | on/off | on | bit 0x0001 / 5010 |
| 26 | Bulk voltage | V | 28.4 V | 4546 / 5027 |
| 27 | Float voltage | V | 27.4 V | 4547 / 5028 |
| 29 | Low battery cut-off | V (or % with LIB-485) | 24.0 V | 4548 / 5029 |
| 30 | Equalization | on/off | off | bit 0x0002 |
| 31 | Equalization voltage | V | 27.0 V (factory 29.2) | 4549 / 5030 |
| 33 | Equalization time | min | 60 | 4550 / 5031 |
| 34 | Equalization timeout | min | 120 | 4551 / 5032 |
| 35 | Equalization interval | days | 30 | 4552 / 5033 |
| 36 | Immediate equalization | on/off | off | bit 0x0004 |
| 37 | Grid-tie (export to grid) | OFF / HYd | **OFF** (do not enable) | not identified |
| 38 | Grid export current | A | 2 A | 4554? |
| 39 | Decorative LED (RGB) | LON / LOF | varies | 4561 (read-only) |
| 41 | Dual output | L2F = off | L2F | not identified |
| 42 | Dual output cut-off | V / % | 55% (22.0 V) | 4534 / 4517 |
| 43 | Lithium protocol | manual: PYL / PAC; **display: 48** | **48 — never change** | — |
| 44 | Delayed grid access | dIS / EnA | EnA | 4520 or 4560? |
| 45 | Second output max. load | 20–70% | 33% (≈ 1400 W) | — |

## Useful meanings

- **USB** (code 0): the grid powers the house first.
- **SUB** (1): solar first, then grid, battery last.
- **SBU** (2): solar → battery → grid. With the battery below prog 12, it switches to the grid (bypass) until the battery rises to prog 13.
- **MKS** (3): solar powers the load and the grid makes up the rest; battery as backup. In tests it behaved the same as SUB.
- **CSO** (0): solar first, grid as backup for charging.
- **SNU** (1): solar and grid charge together.
- **OSO** (2): only solar charges the battery.
- **LIL** (6): lithium with BMS communication (the manual calls it LIB-485). With LIB-485 the manual says 12/13/29 are shown in %; here they are shown in V.
- **bP** on the display = **battery not connected** (not bypass).
- **E9** = equalization in progress.
