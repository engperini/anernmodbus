"""Read-only probe: Modbus function 03, slave 5, register 5038, count 1."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from bleak import BleakClient, BleakScanner
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, encrypt_request, decrypt_response
from tools.rwb1_ble_protocol import derive_key, crc16_modbus, consume_fragment

def settings():
    env = {}
    for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            env[key.strip()] = value.strip().strip("\"'")
    return env

async def main():
    env = settings()
    payload = bytes.fromhex('05 03 13 AE 00 01')
    request = payload + crc16_modbus(payload).to_bytes(2, 'little')
    print('Read-only request: slave 5, function 03, register 5038 (0x13AE), count 1')
    device = await BleakScanner.find_device_by_address(env['RWB1_BLE_ADDRESS'], timeout=8)
    if device is None:
        raise TimeoutError('BLE logger not found')
    chunks = {}
    replies = []
    received = asyncio.Event()
    def on_data(_characteristic, data):
        full = consume_fragment(bytes(data), chunks)
        if full is not None:
            replies.append(full)
            received.set()
    async with BleakClient(device, timeout=20) as ble:
        if ble.services.get_service(SERVICE_UUID) is None:
            raise RuntimeError('RWB1 BLE service absent')
        await ble.start_notify(INDICATE_UUID, on_data)
        try:
            encoded = encrypt_request(request, derive_key(env['RWB1_DTU_ID']))
            size = max(1, min(227, ble.mtu_size - 6))
            parts = [encoded[i:i + size] for i in range(0, len(encoded), size)]
            for i, part in enumerate(parts, 1):
                await ble.write_gatt_char(WRITE_UUID, bytes((i, len(parts), len(part))) + part, response=True)
            await asyncio.wait_for(received.wait(), timeout=8)
        finally:
            await ble.stop_notify(INDICATE_UUID)
    response = decrypt_response(replies[-1], derive_key(env['RWB1_DTU_ID']))
    print('Response:', response.hex(' ').upper())
    if crc16_modbus(response[:-2]) != int.from_bytes(response[-2:], 'little'):
        raise ValueError('invalid CRC')
    if response[:3] != bytes.fromhex('05 03 02') or len(response) != 7:
        print('No decodable one-register reply; no write should be attempted')
        return
    print('Decoded little-endian value:', int.from_bytes(response[3:5], 'little'))
    print('Decoded big-endian value:', int.from_bytes(response[3:5], 'big'))

if __name__ == '__main__':
    asyncio.run(main())
