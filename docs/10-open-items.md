# 10 — Open items

| Item | Status | How to resolve |
|---|---|---|
| 4501 codes 0, 1, 2, 5, 6 | not observed | note the value when the inverter is in standby, powering on, in fault, etc. |
| 4553 status flags | **doubtful** | on 11/15 08:42: 4501 = 3 (Battery), 4553 = 0x7614 after the swap, and bit 0x0100 ("on battery") **off**. Revise the bit map by comparing several states |
| 4554 | **probably solved** | index 0–7 of the LCD power-flow screen (manual 5.6 order); 2 and 7 observed and consistent. Confirm 0, 1, 3–6 when they happen (night on battery should give 6 or 7→6) |
| 4555 / 4556 | **hypothesis: event counter** | always equal: 10 (11/13), 11 (11/14), **12** right after the output was cut and restored by toggling program 41 on 11/15 (the inverter itself was not restarted). Probably a counter of output on/off (or similar) events; confirm the next time the output is cut |
| Prog 37 and 41 (value 0) | register not identified | change one of them with no effect and see which register changes (e.g. 41 with 37 off) |
| Prog 44 (value 1) | 4520 or 4560 | change 44 to dIS and re-read |
| 4519, 4516, 4558, 4559, 4562–4564 | unknown | same |
| LED (prog 39) | state in 4561; write unknown | capture the phone's Bluetooth (HCI snoop) while toggling the LED from the app in local mode; or call `gen/device/config/write` with the current value |
| 4529 warning | probable | confirm when a real warning appears |
| BMS screen 2 ("910") | unknown | note it together with current, PV power and load at different times |
| Detailed BMS data | outside the Modbus block | read the battery BMS directly (RS485/CAN) |
| Two batteries in the BMS | to be confirmed | check whether SOC/limits reflect both (communication cable/DIP) |
| Writes 5019–5021, 5023–5033 and Group D | not tested | first use: write the current value (echo), then a real change checked on the display |
| Programs 12, 13 and 29 in % (BMS battery LIB/LIL) | **not in the readable Modbus space** | 2026-11-15: display 30% (12) / 60% (13) while 4544/4545 read 24.5/27.0 V. FC06 of 30 to 5025 was refused with exception 3 (illegal value), so 5025 takes volts only. Read-only scan (FC03): 4001–4100, 4401–4500 and 4565–4700 do not exist; 5001–5038 exist (see below); no 30/60 anywhere. The vendor cloud app also shows program 12 in **volts** (24.5 V) in BMS mode, so the app reads the same voltage register: the % values seem not to be exposed over the dongle at all. Set them on the inverter display |
| 5001, 5003, 5011–5016 | unknown | readable, all 0 on 2026-11-15. Candidates for programs 37/41/44, but 44 (EnA) should not read 0 |
| Vendor app "Data details" (2026-11-15 11:08-11:23) | clues | Working State **Invert Mode** while 4501 = 3 (so 3 = invert mode). Grid State "connected but relay not turned on", Mains relay OFF, PV "normal access", BatState "discharge", with 4553 = 0x7614 (bit 0x0100 off): 0x0100 may mean "mains relay on" rather than "on battery". Program 37 (grid-tie) OFF, **38 = 2.0 A** and 41 (dual output) off are shown by the app, but 4554 read **7** at the same time, so **4554 is not program 38**; it is the LCD power-flow screen index (see 4554 above). The bridge now publishes the raw unknown registers (sensor "Unknown registers (raw)") to correlate them over time |
