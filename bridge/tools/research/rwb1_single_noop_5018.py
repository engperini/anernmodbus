"""One authorized no-change write: only 05 06 13 9A 00 01 6D 25, after 4537 == 1."""
import asyncio
import os
import sys
sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from bleak import BleakClient, BleakScanner
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, encrypt_request, decrypt_response
from tools.rwb1_ble_protocol import consume_fragment, crc16_modbus, derive_key

READ = bytes.fromhex('05 03 11 B9 00 01')
READ += crc16_modbus(READ).to_bytes(2, 'little')
WRITE = bytes.fromhex('05 06 13 9A 00 01 6D 25')

def validate(frame):
    if len(frame) < 5 or crc16_modbus(frame[:-2]) != int.from_bytes(frame[-2:], 'little'):
        raise ValueError('Modbus CRC/length invalid: ' + frame.hex(' '))
    if frame[0] != 5:
        raise ValueError('Unexpected slave: ' + frame.hex(' '))

def read_value(frame):
    validate(frame)
    if len(frame) != 7 or frame[:3] != b'\x05\x03\x02':
        raise ValueError('Unexpected 4537 read response: ' + frame.hex(' '))
    return int.from_bytes(frame[3:5], 'little')

async def main():
    address = os.environ['RWB1_BLE_ADDRESS']
    key = derive_key(os.environ['RWB1_DTU_ID'])
    device = await BleakScanner.find_device_by_address(address, timeout=8)
    if device is None:
        raise RuntimeError('Logger not found; no write sent')
    chunks = {}
    messages = []
    received = asyncio.Event()
    def on_data(_char, data):
        msg = consume_fragment(bytes(data), chunks)
        if msg is not None:
            messages.append(msg)
            received.set()
    async with BleakClient(device, timeout=20) as client:
        if client.services.get_service(SERVICE_UUID) is None:
            raise RuntimeError('Unexpected GATT service; no write sent')
        await client.start_notify(INDICATE_UUID, on_data)
        async def transact(request):
            chunks.clear(); messages.clear(); received.clear()
            encrypted = encrypt_request(request, key)
            max_payload = max(1, min(227, client.mtu_size - 6))
            fragments = [encrypted[i:i+max_payload] for i in range(0, len(encrypted), max_payload)]
            for idx, payload in enumerate(fragments, 1):
                await client.write_gatt_char(WRITE_UUID, bytes((idx, len(fragments), len(payload))) + payload, response=True)
            await asyncio.wait_for(received.wait(), timeout=8)
            return decrypt_response(messages[-1], key)
        try:
            before_frame = await transact(READ)
            before = read_value(before_frame)
            print('Before 4537:', before, 'RX:', before_frame.hex(' '), flush=True)
            if before != 1:
                print('STOP: 4537 differs from 1; no write sent', flush=True)
                return
            print('Sending exactly one Modbus write:', WRITE.hex(' '), flush=True)
            try:
                reply = await transact(WRITE)
            except Exception as exc:
                print('STOP: write did not yield valid envelope:', repr(exc), flush=True)
                return
            print('Write RX:', reply.hex(' '), flush=True)
            try:
                validate(reply)
            except ValueError as exc:
                print('STOP:', exc, flush=True)
                return
            if reply != WRITE:
                print('STOP: response is not identical echo; no further Modbus requests', flush=True)
                return
            print('Identical echo received', flush=True)
            after_frame = await transact(READ)
            after = read_value(after_frame)
            print('After 4537:', after, 'RX:', after_frame.hex(' '), flush=True)
            if after != 1:
                print('WARNING: readback changed; no further write', flush=True)
        finally:
            await client.stop_notify(INDICATE_UUID)

if __name__ == '__main__':
    asyncio.run(main())
