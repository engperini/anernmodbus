"""One bounded, read-only six-frame snapshot from a saved Siseli gatherProtocol JSON."""
import asyncio
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from bleak import BleakClient, BleakScanner
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, decrypt_response
from tools.rwb1_ble_protocol import derive_key, crc16_modbus, consume_fragment

PROTOCOL = Path('/home/pi/.config/siseli/gather-protocol.json')
OUTDIR = Path('/home/pi/.config/siseli/led-snapshots')
ENV = Path('/home/pi/solar-rwb1-ble/rwb1.env')
LABELS = ('on_before', 'off', 'on_after')

def encode_request(frame, key, cmd_type, cmd_no, uart):
    body = {'CID': 30024, 'PL': {
        'Req': frame.hex().upper(),
        'Uart': {'BaudRate': uart['baudRate'], 'DataBit': uart['dataBit'],
                 'ParityBit': uart['parityBit'], 'StopBit': uart['stopBit']},
        'CmdType': cmd_type, 'CmdNo': cmd_no}}
    raw = json.dumps(body, separators=(',', ':')).encode()
    raw += b'\0' * (-len(raw) % 16)
    e = Cipher(algorithms.AES(key), modes.CBC(key)).encryptor()
    return base64.b64encode(e.update(raw) + e.finalize())

def validated(response, request):
    if len(response) < 5 or response[0] != request[0] or crc16_modbus(response[:-2]) != int.from_bytes(response[-2:], 'little'):
        raise ValueError('response slave/CRC/length invalid')
    start = int.from_bytes(request[2:4], 'big')
    count = int.from_bytes(request[4:6], 'big')
    if response[1:3] != bytes((3, 2*count)) or len(response) != 5 + 2*count:
        raise ValueError('response function/byte count invalid')
    return {'start': start, 'count': count, 'request_hex': request.hex(' '),
            'response_hex': response.hex(' '), 'crc_ok': True,
            'words_big_endian': [int.from_bytes(response[3+i*2:5+i*2], 'big') for i in range(count)],
            'words_little_endian': [int.from_bytes(response[3+i*2:5+i*2], 'little') for i in range(count)]}

def save(label, output):
    OUTDIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(OUTDIR, 0o700)
    path = OUTDIR / (label + '.json')
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(output, f, indent=2)
    print('saved', path, 'validated', sum('crc_ok' in x for x in output['frames']), 'of 6', flush=True)

async def main(label):
    if label not in LABELS:
        raise ValueError('label must be on_before, off, or on_after')
    if (OUTDIR / (label + '.json')).exists():
        raise FileExistsError('snapshot already exists; never overwrite a baseline')
    doc = json.loads(PROTOCOL.read_text())['data']
    entries = [(group, x) for group in ('gatherSingleDevProps', 'gatherSingleDevEvents') for x in doc[group]]
    assert len(entries) == 6
    decoded = []
    for group, item in entries:
        frame = base64.b64decode(item['cmdIn'], validate=True)
        if (len(frame) != 8 or frame[:2] != b'\x05\x03' or
                crc16_modbus(frame[:-2]) != int.from_bytes(frame[-2:], 'little')):
            raise ValueError('saved protocol contains non-allowlisted frame')
        decoded.append((group, item['cmdNo'], frame))
    env = dict(line.split('=', 1) for line in ENV.read_text().splitlines()
               if '=' in line and not line.lstrip().startswith('#'))
    env = {k.strip():v.strip().strip("\"'") for k,v in env.items()}
    key = derive_key(env['RWB1_DTU_ID'])
    output = {'label': label, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'source': 'saved gatherProtocol.json; BLE read-only function 03', 'frames': []}
    try:
        device = await BleakScanner.find_device_by_address(env['RWB1_BLE_ADDRESS'], timeout=12)
        if device is None:
            raise TimeoutError('BLE logger not discovered')
        queue = asyncio.Queue()
        chunks = {}
        def on_data(_ch, data):
            full = consume_fragment(bytes(data), chunks)
            if full is not None:
                queue.put_nowait(full)
        async with BleakClient(device, timeout=20) as client:
            if client.services.get_service(SERVICE_UUID) is None:
                raise ValueError('RWB1 GATT service not found')
            await client.start_notify(INDICATE_UUID, on_data)
            try:
                size = max(1, min(227, client.mtu_size - 6))
                for index,(group,cmd_no,request) in enumerate(decoded):
                    print('read',index+1,'start',int.from_bytes(request[2:4],'big'),
                          'count',int.from_bytes(request[4:6],'big'),flush=True)
                    encrypted = encode_request(request,key,group,cmd_no,doc['uart'])
                    parts = [encrypted[i:i+size] for i in range(0,len(encrypted),size)]
                    for n,part in enumerate(parts,1):
                        await asyncio.wait_for(client.write_gatt_char(WRITE_UUID,bytes((n,len(parts),len(part)))+part,response=True),timeout=8)
                    response = decrypt_response(await asyncio.wait_for(queue.get(),timeout=12),key)
                    record = validated(response,request)
                    record['group'] = group
                    record['index'] = index
                    output['frames'].append(record)
            finally:
                if client.is_connected:
                    await client.stop_notify(INDICATE_UUID)
    finally:
        if output['frames']:
            save(label,output)
    if len(output['frames']) != 6:
        raise ValueError('incomplete six-frame snapshot')

if __name__=='__main__':
    asyncio.run(main(sys.argv[1]))
