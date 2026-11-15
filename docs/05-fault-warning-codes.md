# 05 — Fault and warning codes

Source: printed manual (photos in `images/04-manual/manual-codigos-*.jpg`).

## 4530 — Fault (0 = no fault)

### Inverter (manual 5.9)

| Code | Fault |
|---|---|
| 01 | Fan locked while the inverter is off |
| 02 | Over-temperature |
| 03 | Battery voltage high |
| 04 | Battery voltage low |
| 05 | Output short circuit or internal over-temperature |
| 06 | Output voltage high |
| 07 | Overload (time-out) |
| 08 | Bus voltage high |
| 09 | Bus soft-start failure |
| 51 | Over-current or surge |
| 52 | Bus voltage low |
| 53 | Inverter soft-start failure |
| 55 | DC voltage on AC output |
| 57 | Current sensor failure |
| 58 | Output voltage low |
| 59 | PV voltage over limit |

### Battery / BMS ("Battery fault code")

| Code | Fault |
|---|---|
| 21 | Cell over-voltage |
| 22 | Cell under-voltage |
| 23 | Pack over-voltage |
| 24 | Pack under-voltage |
| 25 | Charge over-current |
| 26 | Discharge over-current |
| 27 | Cell over-temperature while charging |
| 28 | Cell over-temperature while discharging |
| 29 | Cell under-temperature while charging |
| 30 | Cell under-temperature while discharging |
| 31 | Ambient over-temperature |
| 32 | Ambient under-temperature |
| 33 | MOS over-temperature |
| 35 | Battery short circuit |
| 36 | Charge over-voltage |
| 37 | System failure |
| 39 | Charge MOS failure |
| 40 | Discharge MOS failure |
| 41 | Temperature sensor failure |
| 42 | Cell failure |
| 43 | Sampling communication failure |
| **61** | **BMS communication failure** — with LIL/LIB-485 the inverter **shuts off the output** |

## 4529 — Warning (0 = no warning) 🟡

### Inverter (manual 5.10)

| Code | Warning |
|---|---|
| 01 | Fan locked while the inverter is on |
| 03 | Battery overcharged |
| 04 | Low battery |
| 07 | Overload |
| 10 | Output power derating |
| 15 | Low PV energy |
| E9 | Equalization in progress (numeric code unknown) |
| bP | Battery not connected (numeric code unknown) |

### Battery / BMS ("Battery Alarm Code")

| Code | Warning |
|---|---|
| 21–26 | Same as faults 21–26 |
| 27–30 | Cell temperature out of range (same order as the faults) |
| 34 | Battery capacity very low |
| 44 | Cell voltage imbalance |
| 45 | Cell temperature imbalance |
| 46 | Internal communication alarm |

Unknown code → show "Code N".

## Recommended alerts in Home Assistant

- Fault ≠ 0 → immediate notification with the text.
- Fault 61 → **critical** notification: "BMS communication lost — the inverter may shut off the output."
- Warning ≠ 0 for more than 2 min → normal notification.
- Bridge without data for more than 5 min → notification.
