# 10 — Open items: vendor app (cloud) vs. the Bluetooth bridge

Everything the vendor cloud app shows or sets, compared with what the Bluetooth bridge
(this project) covers. Only the rows marked ❌ or ⚠️ are open.
Screenshots: `images/02-app-sunhouse/app-settings-2026-11-15-*.jpg` (settings) and
`app-data-details-2026-11-15-*.jpg` (readings), taken on 2026-11-15.

Legend: ✅ read and write · 📖 read only · ⚠️ partial · ❌ missing

## Settings

| Prog | App menu → item | Bluetooth bridge | Open point |
|---|---|---|---|
| 01 | Load setting → Output Source Priority | ✅ 4537 / 5018 | |
| 02 | Equalization → Max Total Charge Current | ✅ 4541 / 5022 | |
| 03 | Grid → AC Input Range | ✅ 4538 / 5019 | |
| 05 | Equalization → Battery Type | ✅ 4539 / 5020 | |
| 06 | Inverter → Over Load Restart | ✅ bit 4535 / 5005 | |
| 07 | Inverter → Over temperature auto restart | ✅ bit 4535 / 5006 | |
| 09 | Load setting → Output Frequency | ✅ 4540 / 5021 | |
| 10 | Load setting → Output Voltage | ✅ 4542 / 5023 | |
| 11 | Equalization → Utility Charge Current | ✅ 4543 / 5024 | |
| 12 | Equalization → Utility Mode Vol SBU Priority | ⚠️ volts ✅ 4544 / 5025; % (BMS battery) not exposed | the app shows volts too; % only on the display |
| 13 | Equalization → Battery Mode Vol SBU Priority | ⚠️ volts ✅ 4545 / 5026; % not exposed | same |
| 16 | Equalization → Charging Priority | ✅ 4536 / 5017 | |
| 18 | Inverter → buzzer switch | ✅ bit 4535 / 5002 | |
| 19 | Inverter → Return To Default Display Screen | ✅ bit 4535 / 5008 | |
| 20 | Inverter → LCD backlight switch | ✅ bit 4535 / 5004 | |
| 22 | Inverter → Beeps when high priority power is connected | ✅ bit 4535 / 5007 | |
| 23 | Inverter → Overload to bypass | ✅ bit 4535 / 5009 | |
| 25 | Inverter → Record Fault Code | ✅ bit 4535 / 5010 | |
| 26 | Equalization → Bulk Charging Voltage | ✅ 4546 / 5027 | |
| 27 | Equalization → Floating Charging Voltage | ✅ 4547 / 5028 | |
| 29 | Equalization → Low Battery Cut Off Voltage | ⚠️ volts ✅ 4548 / 5029; % not exposed | same as 12 |
| 30 | Equalization → Battery Equalization | 📖 bit 0x0002 of 4535 | ❌ write address unknown |
| 31 | Equalization → Battery Equalization Voltage | ✅ 4549 / 5030 | |
| 33 | Equalization → Battery Equalization Time | ✅ 4550 / 5031 | |
| 34 | Equalization → Battery Equalization Timeout | ✅ 4551 / 5032 | |
| 35 | Equalization → Battery Equalization Interval | ✅ 4552 / 5033 | |
| 36 | Equalization → Equalization Activate Immediate | 📖 bit 0x0004 of 4535 | ❌ write address unknown |
| 37 | Grid → GRID grid switch | ❌ | register unknown (app reads it as OFF) |
| 38 | Grid → GRID-tie current | ❌ | register unknown (app reads 2.0 A; 4554 is not it) |
| 39 | Inverter → LED pattern switch | 📖 4561 | ❌ write refused at 5042; address unknown |
| 41 | Load setting → Dual output switch | ❌ | register unknown (app reads off); no change seen in 4501–4564 when toggled |
| 42 | Load setting → Dual output turn off voltage point | 📖 4517 (V) and 4534 (%) | ❌ write address unknown |
| 00 | System → One Click Restore To Factory | ❌ | not planned (destructive) |

Programs on the display but **not in the app**: 43 (lithium protocol), 44 (delayed grid
access: tested, not exposed over the dongle) and 45 (max second load).

Notes for the ❌ rows:
- The app reads only the blocks 4501–4521, 4521–4528, 4536–4564, 4553, 4529 and 4530
  (docs/02), so 37, 38 and 41 must be somewhere in those; zero-valued candidates are
  4516, 4519, 4558, 4559, 4562–4564 (37/41 read "off" = 0).
- Writes follow read + 481 for the known settings, but 4561 + 481 = 5042 (LED) is refused,
  so the extra settings may use another address or another command of the dongle.

## Readings

| App "Data details" item | Bluetooth bridge |
|---|---|
| Working State ("Invert Mode") | ✅ 4501 → Operation mode |
| PV Input Voltage / Power, Generation Power | ✅ 4504, 4505 |
| AC Input Voltage / Frequency | ✅ 4502, 4503 |
| Mains Input Range | ✅ 4538 |
| Battery Type / Voltage / Capacity (SOC) | ✅ 4539, 4506, 4507 |
| Battery Charging / Discharge Current | ✅ 4508, 4509 |
| Output Voltage / Frequency / Apparent / Active Power, Load Percentage | ✅ 4510–4514 |
| NTC maximum temperature | ✅ 4557 |
| Output turn off voltage point | ✅ 4517 |
| Nominal values, Battery Piece (24 V), Main CPU Version | ✅ 4518, 4521–4528 |
| LED pattern switch | ✅ 4561 |
| All settings listed above | ✅ (see Settings) |
| **PV Status** ("Normal access in working mode"), **Photovoltaic access flag** | ❌ probably bits of 4553 |
| **Grid State** ("connected but relay not turned on"), **Mains relay status** | ❌ probably bits of 4553 (0x0100 = mains relay on?) |
| **BatState** ("discharge") | ❌ probably bits of 4553 |
| **Load Status** ("Normal working state") | ❌ probably bits of 4553 |
| Grid connected switch / current set, Dual output switch | ❌ see 37, 38, 41 |

The bridge also shows what the app does not: fault and warning text (4530, 4529), the LCD
power-flow screen (4554), and the raw unknown registers.

How to close the 4553 rows: note the app's PV/Grid/Bat/Load status texts together with the
"Status flags (4553)" sensor in a few different situations (night on battery, grid charging,
bypass) and match the bits.
