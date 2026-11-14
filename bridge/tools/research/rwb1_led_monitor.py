"""Bounded local read-only monitor of Modbus 0x03 / slave 5 / register 5038."""
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from bleak import BleakClient, BleakScanner
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, encrypt_request, decrypt_response
from tools.rwb1_ble_protocol import derive_key, crc16_modbus, consume_fragment


def settings():
    env = {}
    for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip("\"'")
    return env


async def monitor():
    env = settings()
    key = derive_key(env['RWB1_DTU_ID'])
    device = await BleakScanner.find_device_by_address(env['RWB1_BLE_ADDRESS'], timeout=12)
    if device is None:
        raise TimeoutError('RWB1 not found; no monitoring performed')
    chunks = {}
    replies = asyncio.Queue()
    def on_data(_characteristic, data):
        message = consume_fragment(bytes(data), chunks)
        if message is not None:
            replies.put_nowait(message)
    body = bytes.fromhex('05 03 13 AE 00 01')
    request = body + crc16_modbus(body).to_bytes(2, 'little')
    async with BleakClient(device, timeout=25) as ble:
        if ble.services.get_service(SERVICE_UUID) is None:
            raise RuntimeError('RWB1 BLE service absent')
        await ble.start_notify(INDICATE_UUID, on_data)
        print('MONITOR_READY register=5038 read_only=true duration=180s', flush=True)
        until = time.monotonic() + 180
        try:
            while time.monotonic() < until:
                encoded = encrypt_request(request, key)
                size = max(1, min(227, ble.mtu_size - 6))
                parts = [encoded[i:i+size] for i in range(0, len(encoded), size)]
                for i, part in enumerate(parts, 1):
                    await ble.write_gatt_char(WRITE_UUID, bytes((i, len(parts), len(part)))+part, response=True)
                try:
                    response = decrypt_response(await asyncio.wait_for(replies.get(), timeout=5), key)
                    if len(response) != 7 or response[:3] != b'\x05\x03\x02' or crc16_modbus(response[:-2]) != int.from_bytes(response[-2:], 'little'):
                        raise ValueError('unexpected response')
                    value = int.from_bytes(response[3:5], 'big')
                    print(datetime.now().astimezone().isoformat(timespec='seconds'), '5038=', value, flush=True)
                except (asyncio.TimeoutError, ValueError) as exc:
                    print(datetime.now().astimezone().isoformat(timespec='seconds'), 'READ_ERROR', str(exc), flush=True)
                await asyncio.sleep(2)
        finally:
            await ble.stop_notify(INDICATE_UUID)

if __name__ == '__main__':
    asyncio.run(monitor())
