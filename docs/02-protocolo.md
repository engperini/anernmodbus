# 02 — Protocolo

## Transporte

```
Inversor  ⇄  porta de comunicação  ⇄  dongle Solar Plug RWB1  ⇄  BLE  ⇄  ponte (Raspberry Pi)  ⇄  MQTT  ⇄  Home Assistant
```

- O dongle encapsula **Modbus RTU** (com CRC) nas mensagens BLE. A ponte envia o quadro Modbus e recebe a resposta.
- GATT: serviço `FEE7`, escrita `FED5`, indicação `FED6`; quadros cifrados e fragmentados com cabeçalho de 3 bytes (`bridge/tools/rwb1_ble_protocol.py`, `bridge/tools/ble_modbus_read.py`). As palavras vêm em little-endian. Uma leitura FC03 de 4501 com 64 registradores funciona (testado em 15/11).
- O dongle tem um modo "near" (BLE local) no app: o servidor da Siseli gera o comando e o celular envia por BLE. Rotas vistas no app: `/near/dtu/gatherProtocol`, `/near/dtu/device/attribute/groups`, `/near/dtu/gen/device/config/write` (exigem token da conta). Não são necessárias para a ponte local.

## Modbus

| Item | Valor |
|---|---|
| Escravo | `5` |
| Leitura | `FC03`, bloco `4501–4564` (holding registers) |
| Escrita | **somente** `FC06` (um registrador) |
| Endereço de escrita | **leitura + 481** (ex.: 4537 → 5018) |
| Escala | tensões ÷10, frequências ÷10, correntes e potências inteiras |

### Quadros de leitura usados pelo app (do protocolo baixado da nuvem, todos com CRC válido)

| Quadro | Início | Qtd | Uso |
|---|---|---|---|
| `05 03 11 95 00 15 90 91` | 4501 | 21 | propriedades (telemetria) |
| `05 03 11 A9 00 08 90 94` | 4521 | 8 | propriedades |
| `05 03 11 B8 00 1D 01 5E` | 4536 | 29 | propriedades (configuração) |
| `05 03 11 C9 00 01 50 8C` | 4553 | 1 | propriedades |
| `05 03 11 B1 00 01 D0 95` | 4529 | 1 | eventos (aviso) |
| `05 03 11 B2 00 01 20 95` | 4530 | 1 | eventos (falha) |

### Respostas de erro (formato do fabricante)

| Resposta | Significado |
|---|---|
| `05 03 82 E1 50` | FC03 em endereço inválido (0x80 + 03 com código 2). Ex.: 5000, 5039, 5040 |
| `05 86 82 83 C0` | FC06 em endereço que não aceita escrita (código 2). Ex.: 4561, 5042 |
| `05 90 81 CD A1` | FC10 não suportada (código 1) |

Notas:
- Leitura em bloco falha se o bloco incluir um endereço inválido. Ex.: `5000–5040` falha; `5001–5038` funciona (5037 deu resposta inutilizável).
- A faixa 50xx pode ser lida (espelho dos ajustes), mas a fonte de verdade para estado é a 45xx.

### Exemplos de escrita (CRC calculado e conferido)

| Ação | Quadro | Resposta OK |
|---|---|---|
| Saída = SUB (5018 ← 1) | `05 06 13 9A 00 01 6D 25` | eco idêntico |
| Carregador = CSO (5017 ← 0) | `05 06 13 99 00 00 5C E5` | eco |
| Carregador = SNU (5017 ← 1) | `05 06 13 99 00 01 9D 25` | eco |
| Carregador = OSO (5017 ← 2) | `05 06 13 99 00 02 DD 24` | eco |
| (família) Carregador = só solar 3 | `05 06 13 99 00 03 1C E4` | — |

Fluxo seguro de escrita (usado na ponte):
1. Ler o valor atual (FC03 no registrador 45xx).
2. Validar faixa e regras entre parâmetros.
3. Enviar **um** FC06 em (45xx + 481).
4. Exigir eco idêntico.
5. Reler o 45xx e conferir.
6. Em erro/recusa: registrar e **não repetir**.

## Bytes invertidos

Os registradores de bitmask **4535** e **4553** vêm com os bytes trocados em relação ao mapa PowMr.

- 4535 = 292 = `0x0124` → valor real `0x2401`.
- 4553 = 5478 = `0x1566` → valor real `0x6615`.

Decodificação em `03-mapa-registradores.md`.

## CRC Modbus (referência)

```python
def crc16(b: bytes) -> bytes:
    c = 0xFFFF
    for x in b:
        c ^= x
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return bytes([c & 0xFF, c >> 8])   # little-endian no quadro

frame = bytes([5, 6, 0x13, 0x9A, 0, 1])
print((frame + crc16(frame)).hex(" "))  # 05 06 13 9a 00 01 6d 25
```
