# 02 — Protocol

## Transport

```
Inverter  ⇄  communication port  ⇄  Solar Plug RWB1 dongle  ⇄  BLE  ⇄  bridge (Raspberry Pi)  ⇄  MQTT  ⇄  Home Assistant
```

- The dongle wraps **Modbus RTU** (with CRC) inside BLE messages. The bridge sends the Modbus frame and receives the response.
- GATT: service `FEE7`, write `FED5`, indication `FED6`; frames are encrypted and fragmented with a 3-byte header (`bridge/tools/rwb1_ble_protocol.py`, `bridge/tools/ble_modbus_read.py`). Words arrive little-endian. An FC03 read of 4501 with 64 registers works (tested on 11/15).
- The dongle has a "near" (local BLE) mode in the app: Siseli's server generates the command and the phone sends it over BLE. Routes seen in the app: `/near/dtu/gatherProtocol`, `/near/dtu/device/attribute/groups`, `/near/dtu/gen/device/config/write` (require an account token). They are not needed for the local bridge.

## Modbus

| Item | Value |
|---|---|
| Slave | `5` |
| Read | `FC03`, block `4501–4564` (holding registers) |
| Write | `FC06` **only** (single register) |
| Write address | **read + 481** (e.g. 4537 → 5018) |
| Scale | voltages ÷10, frequencies ÷10, currents and powers as integers |

### Read frames used by the app (from the protocol downloaded from the cloud, all with valid CRC)

| Frame | Start | Count | Use |
|---|---|---|---|
| `05 03 11 95 00 15 90 91` | 4501 | 21 | properties (telemetry) |
| `05 03 11 A9 00 08 90 94` | 4521 | 8 | properties |
| `05 03 11 B8 00 1D 01 5E` | 4536 | 29 | properties (settings) |
| `05 03 11 C9 00 01 50 8C` | 4553 | 1 | properties |
| `05 03 11 B1 00 01 D0 95` | 4529 | 1 | events (warning) |
| `05 03 11 B2 00 01 20 95` | 4530 | 1 | events (fault) |

### Error responses (manufacturer format)

| Response | Meaning |
|---|---|
| `05 03 82 E1 50` | FC03 at an invalid address (0x80 + 03 with code 2). E.g. 5000, 5039, 5040 |
| `05 86 82 83 C0` | FC06 at an address that does not accept writes (code 2). E.g. 4561, 5042 |
| `05 90 81 CD A1` | FC10 not supported (code 1) |

Notes:
- A block read fails if the block includes an invalid address. E.g. `5000–5040` fails; `5001–5038` works (5037 returned an unusable response).
- The 50xx range can be read (a mirror of the settings), but the source of truth for state is 45xx.

### Write examples (CRC computed and checked)

| Action | Frame | OK response |
|---|---|---|
| Output = SUB (5018 ← 1) | `05 06 13 9A 00 01 6D 25` | identical echo |
| Charger = CSO (5017 ← 0) | `05 06 13 99 00 00 5C E5` | echo |
| Charger = SNU (5017 ← 1) | `05 06 13 99 00 01 9D 25` | echo |
| Charger = OSO (5017 ← 2) | `05 06 13 99 00 02 DD 24` | echo |
| (family) Charger = solar only 3 | `05 06 13 99 00 03 1C E4` | — |

Safe write flow (used in the bridge):
1. Read the current value (FC03 on register 45xx).
2. Validate the range and the cross-parameter rules.
3. Send **one** FC06 to (45xx + 481).
4. Require an identical echo.
5. Re-read 45xx and check.
6. On error/refusal: log it and **do not retry**.

## Swapped bytes

The bitmask registers **4535** and **4553** arrive with their bytes swapped relative to the PowMr map.

- 4535 = 292 = `0x0124` → actual value `0x2401`.
- 4553 = 5478 = `0x1566` → actual value `0x6615`.

Decoding in `03-register-map.md`.

## Modbus CRC (reference)

```python
def crc16(b: bytes) -> bytes:
    c = 0xFFFF
    for x in b:
        c ^= x
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return bytes([c & 0xFF, c >> 8])   # little-endian in the frame

frame = bytes([5, 6, 0x13, 0x9A, 0, 1])
print((frame + crc16(frame)).hex(" "))  # 05 06 13 9a 00 01 6d 25
```
