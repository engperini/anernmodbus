# 06 — BMS and batteries

## Inverter ↔ BMS communication

- Works with **prog 05 = LIL** and **prog 43 = 48**. The manual mentions PYL/PAC for prog 43, but this firmware shows a number; **48 is the value that works — do not change it**.
- Evidence: SOC comes from the BMS (4507), charge limits are recognized, the display shows the BMS screens.
- External reports of other Anern units using 43 = 49 for a JK BMS; does not apply here.
- With two batteries in parallel, check whether the battery connected to the inverter aggregates the data of both (communication cable between them and address/DIP per the battery manual).

## BMS screens on the display

Access: main screen, stepping forward with DOWN (the manual says to hold ESC; on this unit just navigating is enough). Photos in `images/05-display-inversor/bms-*.jpg` and the manual in `images/04-manual/manual-telas-bms-p12.jpg`.

| Screen | Manual (left / right) | Display on 11/14 | Note |
|---|---|---|---|
| 1 | Total voltage / SOC | 26.6 V / 39% | same as the manual |
| 2 | Charge / discharge current | 0 A / **910** | **different**: 910 varies a lot, no unit; it is not the charge current (checked). Meaning unknown |
| 3 | Rated capacity (Ah) / cycles | **24.0 V** / 6 | **different**: shows rated voltage; cycles = 6 |
| 4 | MOS min. / max. | 25.2 / 29.2 °C | same |
| 5 | Cell max. / min. | 3.33 / 3.31 V | same |
| 6 | Cell temp. max. / min. | 26.2 / 26.2 °C | same |

Differences on screens 2 and 3 → firmware differs from the manual.

**None of this data appears in the Modbus block 4501–4564** (no value such as 333, 262, 292, 910 in the dump). Getting it into HA would require reading the BMS directly (battery RS485/CAN).

## Health on 11/14/2026

- Cells between 3.31 and 3.33 V (20 mV difference): well balanced.
- Temperatures 25–29 °C: normal.
- 6 cycles: battery practically new.

## Recommended battery settings (LiFePO4 24 V, 8S)

| Setting | Value in use | Safe range |
|---|---|---|
| Bulk (26) | 28.4 V | 26.0–28.8 V |
| Float (27) | 27.4 V | 26.0–28.8 V, ≤ bulk |
| Cut-off (29) | 24.0 V | 24.0–25.0 V, < back to grid |
| Back to grid (12) | 24.5 V | 21.0–25.5 V |
| Back to battery (13) | 27.0 V | 24.0–29.0 V, > back to grid |
| Total current (02) | 70 A (2 batteries) | ≤ 100 A per battery |
