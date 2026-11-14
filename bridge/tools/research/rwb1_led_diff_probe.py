"""Bounded read-only snapshot of settings registers; no Modbus write functions."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from bleak import BleakClient, BleakScanner
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, encrypt_request, decrypt_response
from tools.rwb1_ble_protocol import derive_key, crc16_modbus, consume_fragment

# Only the 20 individually readable extended addresses; unsupported ranges can disconnect GATT.
ADDRESSES = list(range(4522, 4542))


def settings():
    env = {}
    for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip("\"'")
    return env


async def main():
    state = sys.argv[1] if len(sys.argv) == 2 else None
    if state not in ('off', 'on'):
        raise SystemExit('usage: rwb1_led_diff_probe.py {off|on}')
    env = settings()
    key = derive_key(env['RWB1_DTU_ID'])
    device = await BleakScanner.find_device_by_address(env['RWB1_BLE_ADDRESS'], timeout=8)
    if device is None:
        raise TimeoutError('BLE logger not found')
    chunks = {}
    messages = asyncio.Queue()
    def on_data(_characteristic, data):
        full = consume_fragment(bytes(data), chunks)
        if full is not None:
            messages.put_nowait(full)
    results = {}
    async with BleakClient(device, timeout=20) as ble:
        if ble.services.get_service(SERVICE_UUID) is None:
            raise RuntimeError('RWB1 service absent')
        await ble.start_notify(INDICATE_UUID, on_data)
        try:
            for address in ADDRESSES:
                body = b'\x05\x03' + address.to_bytes(2, 'big') + b'\x00\x01'
                request = body + crc16_modbus(body).to_bytes(2, 'little')
                encoded = encrypt_request(request, key)
                size = max(1, min(227, ble.mtu_size - 6))
                parts = [encoded[i:i + size] for i in range(0, len(encoded), size)]
                for i, part in enumerate(parts, 1):
                    await ble.write_gatt_char(WRITE_UUID, bytes((i, len(parts), len(part))) + part, response=True)
                try:
                    raw = await asyncio.wait_for(messages.get(), timeout=3)
                    response = decrypt_response(raw, key)
                    if crc16_modbus(response[:-2]) != int.from_bytes(response[-2:], 'little'):
                        raise ValueError('invalid CRC')
                    if response[:3] == b'\x05\x03\x02' and len(response) == 7:
                        results[str(address)] = int.from_bytes(response[3:5], 'big')
                    else:
                        results[str(address)] = 'unsupported:' + response.hex().upper()
                except (asyncio.TimeoutError, ValueError, KeyError) as exc:
                    results[str(address)] = 'error:' + type(exc).__name__
        finally:
            await ble.stop_notify(INDICATE_UUID)
    target = Path('/tmp/rwb1_led_extended_' + state + '_settings.json')
    target.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')
    print('Read-only state:', state, 'registers:',len(results),'numeric:',sum(isinstance(v,int) for v in results.values()))
    print('Saved:',target)
    print('Values:',json.dumps(results,sort_keys=True))
    if state == 'on':
        old = Path('/tmp/rwb1_led_extended_off_settings.json')
        if old.exists():
            before = json.loads(old.read_text())
            print('CHANGES:',json.dumps({k:{'off':before[k],'on':v} for k,v in results.items() if k in before and isinstance(v,int) and isinstance(before[k],int) and v!=before[k]},sort_keys=True))

if __name__ == '__main__':
    asyncio.run(main())
