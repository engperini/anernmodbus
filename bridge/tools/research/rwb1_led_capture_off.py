import asyncio, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from bleak import BleakClient, BleakScanner
sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, encrypt_request, decrypt_response
from tools.rwb1_ble_protocol import consume_fragment, crc16_modbus, derive_key

base = Path('/home/pi/.config/siseli/led-snapshots')
prior = json.loads((base/'on_before.json').read_text())
assert len(prior['frames']) == 6 and all(f['crc_ok'] for f in prior['frames'])
prior['frames'] = [f for f in prior['frames'] if f['start'] == 4536]
env = dict(line.strip().split('=', 1) for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
address = env['RWB1_BLE_ADDRESS'].strip().strip('"\'')
key = derive_key(env['RWB1_DTU_ID'].strip().strip('"\''))

async def main():
    device = await BleakScanner.find_device_by_address(address, timeout=12)
    if device is None: raise RuntimeError('device not found')
    rows = []
    async with BleakClient(device, timeout=20) as client:
        assert client.services.get_service(SERVICE_UUID) is not None
        chunks = {}; messages = []; received = asyncio.Event()
        def on_data(_, data):
            message = consume_fragment(bytes(data), chunks)
            if message is not None: messages.append(message); received.set()
        await client.start_notify(INDICATE_UUID, on_data)
        try:
            for original in prior['frames']:
                chunks.clear(); messages.clear(); received.clear()
                req = bytes.fromhex(original['request_hex'])
                assert req[0:2] == b'\x05\x03' and crc16_modbus(req[:-2]) == int.from_bytes(req[-2:], 'little')
                encrypted = encrypt_request(req, key)
                max_payload = max(1, min(227, client.mtu_size-6))
                parts = [encrypted[i:i+max_payload] for i in range(0,len(encrypted),max_payload)]
                for i,payload in enumerate(parts,1):
                    await client.write_gatt_char(WRITE_UUID, bytes((i,len(parts),len(payload)))+payload, response=True)
                await asyncio.wait_for(received.wait(), timeout=10)
                rsp = decrypt_response(messages[-1], key)
                count = original['count']
                assert len(rsp) == 5+2*count and rsp[0:3] == bytes((5,3,2*count))
                assert crc16_modbus(rsp[:-2]) == int.from_bytes(rsp[-2:], 'little')
                row = {k:original[k] for k in ('start','count','request_hex','group','index')}
                row.update(response_hex=rsp.hex(' '),crc_ok=True,words_big_endian=[int.from_bytes(rsp[3+i*2:5+i*2],'big') for i in range(count)],words_little_endian=[int.from_bytes(rsp[3+i*2:5+i*2],'little') for i in range(count)])
                rows.append(row)
                print(f"validated {original['start']}/{count}", flush=True)
        finally:
            await client.stop_notify(INDICATE_UUID)
    output = dict(label='off_final',timestamp_utc=datetime.now(timezone.utc).isoformat(),source=prior['source'],frames=rows)
    target=base/'off_final.json'
    assert not target.exists(), 'off file already exists; refusing overwrite'
    with target.open('x') as f: json.dump(output,f,indent=2)
    os.chmod(target,0o600)
    print('saved validated OFF snapshot', flush=True)
asyncio.run(main())
