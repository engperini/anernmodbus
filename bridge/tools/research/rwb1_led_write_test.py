"""Single authorized BLE write test: decimal register 4561, raw value 01 00 only."""
import asyncio, json, sys, os
from pathlib import Path
from datetime import datetime, timezone
from bleak import BleakClient, BleakScanner
sys.path.insert(0, '/home/pi/solar-rwb1-ble')
from tools.ble_modbus_read import SERVICE_UUID, WRITE_UUID, INDICATE_UUID, encrypt_request, decrypt_response
from tools.rwb1_ble_protocol import consume_fragment, crc16_modbus, derive_key

base=Path('/home/pi/.config/siseli/led-snapshots')
prior=json.loads((base/'off_final.json').read_text())
f=prior['frames'][0]
assert f['start']==4536 and f['count']==29 and f['crc_ok'] and f['words_little_endian'][25]==0
assert not (base/'write_test_on.json').exists(), 'existing test result: refusing duplicate write'
env=dict(line.strip().split('=',1) for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
address=env['RWB1_BLE_ADDRESS'].strip().strip('"\'')
key=derive_key(env['RWB1_DTU_ID'].strip().strip('"\''))

def request(function, register, pair):
    raw=bytes((5,function))+register.to_bytes(2,'big')+pair
    return raw+crc16_modbus(raw).to_bytes(2,'little')

async def main():
    device=await BleakScanner.find_device_by_address(address, timeout=12)
    if device is None: raise RuntimeError('device not found')
    chunks={}; messages=[]; event=asyncio.Event()
    def callback(_,data):
        result=consume_fragment(bytes(data),chunks)
        if result is not None: messages.append(result);event.set()
    async with BleakClient(device, timeout=20) as client:
        assert client.services.get_service(SERVICE_UUID) is not None
        await client.start_notify(INDICATE_UUID,callback)
        async def exchange(req):
            chunks.clear();messages.clear();event.clear()
            encrypted=encrypt_request(req,key)
            max_payload=max(1,min(227,client.mtu_size-6))
            parts=[encrypted[i:i+max_payload] for i in range(0,len(encrypted),max_payload)]
            for i,p in enumerate(parts,1):
                await client.write_gatt_char(WRITE_UUID,bytes((i,len(parts),len(p)))+p,response=True)
            await asyncio.wait_for(event.wait(),timeout=12)
            rsp=decrypt_response(messages[-1],key)
            assert crc16_modbus(rsp[:-2])==int.from_bytes(rsp[-2:],'little'), 'response CRC invalid'
            return rsp
        async def read_state():
            req=request(3,4536,(29).to_bytes(2,'big'))
            rsp=await exchange(req)
            assert len(rsp)==63 and rsp[:3]==bytes((5,3,58)),f'unexpected read response: {rsp.hex(" ")}'
            return int.from_bytes(rsp[3+25*2:5+25*2],'little')
        try:
            before=await read_state()
            print('current 4561:',before,flush=True)
            assert before==0,'LED state is not OFF; no write attempted'
            write=request(6,4561,b'\x01\x00')
            print('sending exactly one function-06 write to 4561, raw 01 00',flush=True)
            # Persist intent before the side effect, so a timeout cannot trigger a blind retry.
            target=base/'write_test_on.json'
            result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'register':4561,'before':before,'request_hex':write.hex(' '),'status':'write_attempted_no_retry'}
            with target.open('x') as output: json.dump(result,output,indent=2)
            os.chmod(target,0o600)
            try:
                rsp=await exchange(write)
                result['write_response_hex']=rsp.hex(' ')
                result['write_ack_exact_echo']=rsp==write
                print('write response CRC valid; exact echo:',rsp==write,'response:',rsp.hex(' '),flush=True)
                await asyncio.sleep(2)
                result['after']=await read_state()
                print('current 4561 after write:',result['after'],flush=True)
                result['status']='readback_completed'
            except Exception as exc:
                result['error']=str(exc)
                print('write/readback uncertain:',type(exc).__name__,str(exc),flush=True)
                raise
            finally:
                target.write_text(json.dumps(result,indent=2))
                os.chmod(target,0o600)
        finally:
            await client.stop_notify(INDICATE_UUID)
asyncio.run(main())
