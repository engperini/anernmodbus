"""One-shot, read-only Modbus 0x03 probe of decimal register 331 over RWB1 BLE."""
import asyncio
import os
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
            k, v = line.partition('=')[::2]
            env[k.strip()] = v.strip().strip("\"'")
    return env


async def main():
    slave = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    if slave not in (1, 5):
        raise ValueError('only candidate slaves 1 or 5 permitted')
    env = settings()
    key = derive_key(env['RWB1_DTU_ID'])
    address = env['RWB1_BLE_ADDRESS']
    payload = bytes((slave, 3, 1, 0x4B, 0, 1))  # only read register 331
    request = payload + crc16_modbus(payload).to_bytes(2, 'little')
    print('Read-only request: slave', slave, 'function 03, register 331, count 1')
    dev = await BleakScanner.find_device_by_address(address, timeout=8)
    if dev is None:
        raise TimeoutError('BLE logger not found')
    chunks = {}
    received = asyncio.Event()
    messages = []

    def on_data(_characteristic, data):
        full = consume_fragment(bytes(data), chunks)
        if full is not None:
            messages.append(full)
            received.set()

    async with BleakClient(dev, timeout=20) as ble:
        if ble.services.get_service(SERVICE_UUID) is None:
            raise RuntimeError('RWB1 service not found')
        await ble.start_notify(INDICATE_UUID, on_data)
        try:
            encoded = encrypt_request(request, key)
            size = max(1, min(227, ble.mtu_size - 6))
            parts = [encoded[i:i + size] for i in range(0, len(encoded), size)]
            for i, part in enumerate(parts, 1):
                await ble.write_gatt_char(WRITE_UUID, bytes((i, len(parts), len(part))) + part, response=True)
            await asyncio.wait_for(received.wait(), timeout=8)
        finally:
            await ble.stop_notify(INDICATE_UUID)
    rsp = decrypt_response(messages[-1], key)
    if len(rsp) < 5 or crc16_modbus(rsp[:-2]) != int.from_bytes(rsp[-2:], 'little'):
        raise ValueError('unexpected or CRC-invalid response')
    if rsp[0] != slave:
        raise ValueError('wrong slave')
    if rsp[1] == 0x83:
        print('Modbus exception code:', rsp[2]);return
    if rsp[:3] != bytes((slave, 3, 2)) or len(rsp) != 7:
        print('Unexpected CRC-valid response:', rsp.hex(' ').upper());return
    print('CRC-valid register 331 raw value:', int.from_bytes(rsp[3:5], 'big'))
    print('Raw data bytes:', rsp[3:5].hex().upper())


if __name__ == '__main__':
    asyncio.run(main())
