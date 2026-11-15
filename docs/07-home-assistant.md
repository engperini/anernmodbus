# 07 — Home Assistant dashboard specification

Specification of the final version (11/14/2026, screenshots in `images/06-dashboard-ha/v5-final-*`). It is meant for rebuilding the dashboard from scratch. Entity names are in English.

## Principles

- Controls **always show the value read** from the inverter; the locks only block writing.
- No automatic writes: only when the user changes a control.
- One setting at a time; validation before writing; re-read afterwards.
- Short names, with the program number on every configurable item; no register number or "probable" in the name (status lives in the docs).
- Same font and spacing on all cards; entity cards (no markdown tables, so tapping keeps the history).
- Precision: voltages and frequencies with 1 decimal; currents and powers with none (`suggested_display_precision`). `number` fields in box mode may show "27V" instead of "27.0 V" (HA limitation, acceptable).

## Locks

| Entity | Function |
|---|---|
| `input_boolean.anern_edit_mode` "Inverter edit mode (10 min)" | Enables writing for Groups A, B and D. Turns itself off after 10 min |
| `input_boolean.anern_critical_settings` "Critical settings" | Second lock, required by Group C |

## Control groups

**Group A · priorities** (select)
- Charger source (16) → 5017: CSO / SNU / OSO
- Output source (01) → 5018: USB / SUB / SBU / MKS

**Group B · battery charging** (number, box mode)

| Name | Write | Range | Step | Rule |
|---|---|---|---|---|
| Max current · total (02) | 5022 | 10–100 A | 10 | |
| Max current · grid (11) | 5024 | 2, 10…100 A | | ≤ total (02) |
| Back to grid V (12) | 5025 | 21.0–25.5 V | 0.5 | |
| Back to battery V (13) | 5026 | 24.0–29.0 V | 0.5 | > back to grid |
| Bulk voltage (26) | 5027 | 26.0–28.8 V | 0.1 | |
| Float voltage (27) | 5028 | 26.0–28.8 V | 0.1 | ≤ bulk |
| Low cutoff V (29) | 5029 | 24.0–25.0 V | 0.1 | < back to grid |
| Equaliz. voltage (31) | 5030 | 26.0–28.8 V | 0.1 | |
| Equaliz. time (33) | 5031 | 5–900 min | 5 | |
| Equaliz. timeout (34) | 5032 | 5–900 min | 5 | |
| Equaliz. interval (35) | 5033 | 0–90 days | 1 | |

**BMS batteries (type LIB or LIL):** the inverter display shows programs 12, 13 and 29 in % of SOC (e.g. 30% / 60%), while registers 4544/4545/4548 keep the voltage-mode values. The % registers are unknown, so the bridge treats these three as read-only in that case.

Help line: "One setting at a time. Rules: grid charge current ≤ total; low cutoff < back to grid < back to battery; float ≤ bulk."

**Group C · critical settings** (two locks + a select that only stages the value + a compact "Apply" button with confirmation)
- AC input range (03) → 5019: APL / UPS
- Battery type (05) → 5020: AGM / FLD / USE / LIB / LIC / LIP / LIL
- Output frequency (09) → 5021: 50 / 60 Hz
- Output voltage (10) → 5023: 220 / 230 / 240 V
- Notices: "Lithium with BMS: keep LIL (05)." and "Local grid: 60 Hz / 220 V."

**Group D · on/off** (switch, edit mode; state read from the 4535 bit)
Alarm (18) 5002 · Backlight (20) 5004 · Restart on overload (06) 5005 · Restart on overtemp (07) 5006 · Beep on source loss (22) 5007 · Return to main screen (19) 5008 · Overload bypass (23) 5009 · Fault record (25) 5010

**No control:** programs 37 (grid-tie), 43 (=48, never change), 44, 45 and LED.

## Read-only cards (order)

1. **Notice:** "WARNING — check the battery manual and the BMS limits before changing battery parameters. Grid: 60 Hz / 220 V. The locks turn off after 10 min. Critical settings require both locks and confirmation."
2. Edit locks
3. Group A · Group B · Group C · Group D
4. **Solar:** PV voltage, PV power
5. **Battery:** Voltage, SOC (BMS), Charge current, Discharge current
6. **Grid:** Voltage, Frequency
7. **Output and load:** Voltage, Frequency, Active power, Apparent power, Load percentage
8. **Equipment:** Operating mode (4501 as text), NTC temperature, LED (read-only), Load enabled / Grid active / On battery (4553)
9. **Diagnostics:** Fault (text), Warning (text), Last setting result, Recent data (<5 min), Equalization (30), Immediate equalization (36), Dual output cut-off (42) V and %
10. **Technical open items** (open items only — see `10-open-items.md`)
11. **Equipment information:** CPU version, rated power W/VA, rated AC voltage/current, rated battery voltage, rated output voltage/frequency/current

Do not repeat on read-only cards the values the controls already show.

## MQTT and persistence

- MQTT discovery with `retain` **and** re-sent when HA publishes `online` on `homeassistant/status` (otherwise the entities disappear on every HA restart).
- Keep `unique_id`/`entity_id` stable when renaming (change only the friendly name) so history is not lost.
- Dashboard in **YAML at the path HA actually loads**, versioned in git and with a copy off the Pi.
- Persistence proof: **real reboot of the Pi** (`sudo reboot`), not just an HA restart.
