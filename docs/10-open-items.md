# 10 — Open items

| Item | Status | How to resolve |
|---|---|---|
| 4501 codes 0, 1, 2, 5, 6 | not observed | note the value when the inverter is in standby, powering on, in fault, etc. |
| 4553 status flags | **doubtful** | on 11/15 08:42: 4501 = 3 (Battery), 4553 = 0x7614 after the swap, and bit 0x0100 ("on battery") **off**. Revise the bit map by comparing several states |
| 4554 | prog 38 or battery state | at night, not charging: if it stays at 2 it is prog 38 |
| 4555 / 4556 | unknown (10 → 11) | observe over several days; compare with app fields |
| Prog 37 and 41 (value 0) | register not identified | change one of them with no effect and see which register changes (e.g. 41 with 37 off) |
| Prog 44 (value 1) | 4520 or 4560 | change 44 to dIS and re-read |
| 4519, 4516, 4558, 4559, 4562–4564 | unknown | same |
| LED (prog 39) | state in 4561; write unknown | capture the phone's Bluetooth (HCI snoop) while toggling the LED from the app in local mode; or call `gen/device/config/write` with the current value |
| 4529 warning | probable | confirm when a real warning appears |
| BMS screen 2 ("910") | unknown | note it together with current, PV power and load at different times |
| Detailed BMS data | outside the Modbus block | read the battery BMS directly (RS485/CAN) |
| Two batteries in the BMS | to be confirmed | check whether SOC/limits reflect both (communication cable/DIP) |
| Writes 5019–5021, 5023–5033 and Group D | not tested | first use: write the current value (echo), then a real change checked on the display |
| Programs 12, 13 and 29 in % (BMS battery LIB/LIL) | unknown | the display showed 30% (12) and 60% (13) on 2026-11-15 while 4544/4545 still read 24.5/27.0 V; no 30/60 in 4501–4564 and 5001+ refuses FC03. Find the % registers (other blocks, or HCI snoop of the app) |
