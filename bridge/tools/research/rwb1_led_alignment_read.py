"""Read-only simultaneous protocol-frame and settings-range snapshot; no write functions."""
import asyncio, json, os, sys
from pathlib import Path
from datetime import datetime, timezone
from bleak import BleakClient, BleakScanner
sys.path.insert(0,'/home/pi/solar-rwb1-ble')
from tools.ble_modbus_read import SERVICE_UUID,WRITE_UUID,INDICATE_UUID,encrypt_request,decrypt_response
from tools.rwb1_ble_protocol import consume_fragment,crc16_modbus,derive_key
base=Path('/home/pi/.config/siseli/led-snapshots')
old=json.loads((base/'on_before.json').read_text())
assert len(old['frames'])==6 and all(f['crc_ok'] for f in old['frames'])
target=base/'alignment_on.json'
assert not target.exists(),'snapshot already exists; not overwriting'
env=dict(line.strip().split('=',1) for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
address=env['RWB1_BLE_ADDRESS'].strip().strip('"\'')
key=derive_key(env['RWB1_DTU_ID'].strip().strip('"\''))
def req(start,count):
    raw=bytes((5,3))+start.to_bytes(2,'big')+count.to_bytes(2,'big')
    return raw+crc16_modbus(raw).to_bytes(2,'little')
async def main():
    device=await BleakScanner.find_device_by_address(address,timeout=12)
    if device is None:raise RuntimeError('BLE logger not found')
    chunks={};messages=[];event=asyncio.Event()
    def on_data(_,data):
        msg=consume_fragment(bytes(data),chunks)
        if msg is not None:messages.append(msg);event.set()
    data={'label':'alignment_on','timestamp_utc':datetime.now(timezone.utc).isoformat(),'preflight_4561':None,'frames':[],'settings':[],'errors':[]}
    async with BleakClient(device,timeout=20) as client:
        assert client.services.get_service(SERVICE_UUID) is not None
        await client.start_notify(INDICATE_UUID,on_data)
        async def read(start,count):
            assert (start,count) in [(f['start'],f['count']) for f in old['frames']] or (5001<=start<=5038 and start+count<=5039)
            request=req(start,count);chunks.clear();messages.clear();event.clear()
            enc=encrypt_request(request,key)
            n=max(1,min(227,client.mtu_size-6));parts=[enc[i:i+n] for i in range(0,len(enc),n)]
            for i,p in enumerate(parts,1):
                await client.write_gatt_char(WRITE_UUID,bytes((i,len(parts),len(p)))+p,response=True)
            await asyncio.wait_for(event.wait(),timeout=11)
            rsp=decrypt_response(messages[-1],key)
            assert crc16_modbus(rsp[:-2])==int.from_bytes(rsp[-2:],'little'),'CRC failed'
            if len(rsp)!=5+2*count or rsp[:3]!=bytes((5,3,count*2)):
                raise ValueError('unexpected response shape '+rsp.hex(' '))
            return {'start':start,'count':count,'request_hex':request.hex(' '),'response_hex':rsp.hex(' '),'crc_ok':True,'words_little_endian':[int.from_bytes(rsp[3+i*2:5+i*2],'little') for i in range(count)]}
        try:
            pre=await read(4536,29)
            data['preflight_4561']=pre['words_little_endian'][25]
            print('preflight 4561:',data['preflight_4561'],flush=True)
            assert data['preflight_4561']==1,'physical ON not reflected; stopping before range reads'
            for f in old['frames']:
                row=await read(f['start'],f['count']);data['frames'].append(row)
                print('protocol:',f['start'],f['count'],'validated',flush=True)
            assert next(f for f in data['frames'] if f['start']==4536)['words_little_endian'][25]==1
            # Try one bounded block. If unsupported, split and finally fall back to individual reads.
            async def range_read(start,count):
                try:
                    row=await read(start,count);data['settings'].append(row)
                    print('settings:',start,count,'validated',flush=True)
                except ValueError as exc:
                    data['errors'].append({'start':start,'count':count,'reason':str(exc)})
                    print('settings block rejected:',start,count,flush=True)
                    if count>1:
                        half=count//2
                        await range_read(start,half)
                        await range_read(start+half,count-half)
            await range_read(5001,38)
        finally:
            await client.stop_notify(INDICATE_UUID)
    with target.open('x') as fp:json.dump(data,fp,indent=2)
    os.chmod(target,0o600)
    print('saved read-only snapshot; settings registers:',sum(x['count'] for x in data['settings']),flush=True)
asyncio.run(main())
