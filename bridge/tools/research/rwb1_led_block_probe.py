"""One bounded read-only Modbus 03 snapshot of extended telemetry registers."""
import asyncio, json, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from bleak import BleakClient, BleakScanner
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, encrypt_request, decrypt_response
from tools.rwb1_ble_protocol import derive_key, crc16_modbus, consume_fragment

async def main(state):
    if state != 'on':
        raise ValueError('Only ON snapshot supported; preserve baseline')
    env = dict(line.split('=', 1) for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
    env = {k.strip(): v.strip().strip("\"'") for k,v in env.items()}
    key = derive_key(env['RWB1_DTU_ID'])
    device = await BleakScanner.find_device_by_address(env['RWB1_BLE_ADDRESS'], timeout=12)
    if device is None:
        raise TimeoutError('BLE logger not found')
    replies = asyncio.Queue()
    chunks = {}
    def on_data(_ch, data):
        full = consume_fragment(bytes(data), chunks)
        if full is not None:
            replies.put_nowait(full)
    start, count = 4522, 20
    body = bytes((5, 3)) + start.to_bytes(2, 'big') + count.to_bytes(2, 'big')
    request = body + crc16_modbus(body).to_bytes(2, 'little')
    async with BleakClient(device, timeout=20) as ble:
        if ble.services.get_service(SERVICE_UUID) is None:
            raise ValueError('RWB1 service not found')
        await ble.start_notify(INDICATE_UUID, on_data)
        try:
            encoded = encrypt_request(request, key)
            size = max(1, min(227, ble.mtu_size - 6))
            parts = [encoded[i:i+size] for i in range(0,len(encoded),size)]
            for i,part in enumerate(parts,1):
                await asyncio.wait_for(ble.write_gatt_char(WRITE_UUID, bytes((i,len(parts),len(part)))+part, response=True), timeout=8)
            response = decrypt_response(await asyncio.wait_for(replies.get(), timeout=10), key)
        finally:
            if ble.is_connected:
                await ble.stop_notify(INDICATE_UUID)
    if crc16_modbus(response[:-2]) != int.from_bytes(response[-2:], 'little'):
        raise ValueError('invalid CRC')
    if len(response) != 5+count*2 or response[:3] != bytes((5,3,count*2)):
        print('UNSUPPORTED/UNEXPECTED',response.hex(' ').upper(),flush=True)
        return
    values = {str(start+i):int.from_bytes(response[3+i*2:5+i*2], 'big') for i in range(count)}
    target=Path('/tmp/rwb1_led_extended_on_settings.json')
    target.write_text(json.dumps(values,indent=2,sort_keys=True)+'\n')
    old=json.loads(Path('/tmp/rwb1_led_extended_off_settings.json').read_text())
    changes={k:[old[k],v] for k,v in values.items() if isinstance(old.get(k),int) and old[k]!=v}
    print('time',datetime.now().astimezone().isoformat(timespec='seconds'),'values',json.dumps(values,sort_keys=True),'changes_OFF_to_ON',json.dumps(changes,sort_keys=True),'saved',target,flush=True)

if __name__=='__main__':
    asyncio.run(main(sys.argv[1]))
