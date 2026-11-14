"""Bounded read-only Modbus 0x03 probe for configuration register block 5000..5040."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from bleak import BleakClient, BleakScanner
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, encrypt_request, decrypt_response
from tools.rwb1_ble_protocol import derive_key, crc16_modbus, consume_fragment

START = 5000
COUNT = 41

def settings():
    env = {}
    for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip("\"'")
    return env

async def main():
    env = settings()
    body = bytes((5, 3)) + START.to_bytes(2, 'big') + COUNT.to_bytes(2, 'big')
    request = body + crc16_modbus(body).to_bytes(2, 'little')
    print(f'Only READ function 03, registers {START}..{START+COUNT-1}')
    device = await BleakScanner.find_device_by_address(env['RWB1_BLE_ADDRESS'], timeout=8)
    if device is None:
        raise TimeoutError('BLE logger not found')
    chunks = {}
    replies = []
    ready = asyncio.Event()
    def on_data(_characteristic, data):
        full = consume_fragment(bytes(data), chunks)
        if full is not None:
            replies.append(full)
            ready.set()
    async with BleakClient(device, timeout=20) as ble:
        if ble.services.get_service(SERVICE_UUID) is None:
            raise RuntimeError('BLE service absent')
        await ble.start_notify(INDICATE_UUID, on_data)
        try:
            encoded = encrypt_request(request, derive_key(env['RWB1_DTU_ID']))
            size = max(1, min(227, ble.mtu_size - 6))
            parts = [encoded[i:i + size] for i in range(0, len(encoded), size)]
            for i, part in enumerate(parts, 1):
                await ble.write_gatt_char(WRITE_UUID, bytes((i, len(parts), len(part))) + part, response=True)
            await asyncio.wait_for(ready.wait(), timeout=8)
        finally:
            await ble.stop_notify(INDICATE_UUID)
    response = decrypt_response(replies[-1], derive_key(env['RWB1_DTU_ID']))
    if crc16_modbus(response[:-2]) != int.from_bytes(response[-2:], 'little'):
        raise ValueError('invalid CRC')
    expected = 3 + 2 * COUNT + 2
    if len(response) != expected or response[:3] != bytes((5, 3, 2*COUNT)):
        print('Unsupported/unexpected read reply:',response[:8].hex(' ').upper(), 'length', len(response))
        return
    for i in range(COUNT):
        print(f'{START+i}: {int.from_bytes(response[3+2*i:5+2*i], "big")} (raw {response[3+2*i:5+2*i].hex().upper()})')

if __name__ == '__main__':
    asyncio.run(main())
