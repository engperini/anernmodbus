"""Owner-authorized two-stage BLE test, strictly two allowlisted writes at most."""
import asyncio,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from bleak import BleakClient,BleakScanner
sys.path.insert(0,'/home/pi/solar-rwb1-ble')
from tools.ble_modbus_read import SERVICE_UUID,WRITE_UUID,INDICATE_UUID,encrypt_request,decrypt_response
from tools.rwb1_ble_protocol import crc16_modbus,consume_fragment,derive_key
BASE=Path('/home/pi/.config/siseli/led-snapshots')
TARGET=BASE/'write_test_5042.json'
assert not TARGET.exists(),'test record already exists; never repeat writes'
ON=bytes.fromhex('05 06 13 B2 00 01 ED 2D')
OFF=bytes.fromhex('05 06 13 B2 00 00 2C ED')
assert ON[:6]==bytes.fromhex('05 06 13 b2 00 01') and OFF[:6]==bytes.fromhex('05 06 13 b2 00 00')
assert all(crc16_modbus(x[:-2])==int.from_bytes(x[-2:],'little') for x in (ON,OFF))
assert bytes.fromhex('05 03 02 00 01 88 44')[3:5]==ON[4:6]
old=json.loads((BASE/'alignment_on.json').read_text())
assert old['preflight_4561']==1
env=dict(line.strip().split('=',1) for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
address=env['RWB1_BLE_ADDRESS'].strip().strip('"\'')
key=derive_key(env['RWB1_DTU_ID'].strip().strip('"\''))
record={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status':'initialized','writes_attempted':[]}
def save():
    if TARGET.exists():TARGET.write_text(json.dumps(record,indent=2))
    else:
        with TARGET.open('x') as f:json.dump(record,f,indent=2)
    os.chmod(TARGET,0o600)
async def main():
    device=await BleakScanner.find_device_by_address(address,timeout=12)
    if device is None:raise RuntimeError('logger not found; no write sent')
    chunks={};messages=[];event=asyncio.Event()
    def callback(_,data):
        msg=consume_fragment(bytes(data),chunks)
        if msg is not None:messages.append(msg);event.set()
    async with BleakClient(device,timeout=20) as client:
        assert client.services.get_service(SERVICE_UUID) is not None
        await client.start_notify(INDICATE_UUID,callback)
        async def exchange(request):
            chunks.clear();messages.clear();event.clear()
            encrypted=encrypt_request(request,key)
            n=max(1,min(227,client.mtu_size-6))
            parts=[encrypted[i:i+n] for i in range(0,len(encrypted),n)]
            for i,p in enumerate(parts,1):
                await client.write_gatt_char(WRITE_UUID,bytes((i,len(parts),len(p)))+p,response=True)
            await asyncio.wait_for(event.wait(),timeout=12)
            response=decrypt_response(messages[-1],key)
            if crc16_modbus(response[:-2])!=int.from_bytes(response[-2:],'little'):
                raise ValueError('invalid response CRC')
            return response
        async def read_state():
            raw=bytes.fromhex('05 03 11 b8 00 1d')
            req=raw+crc16_modbus(raw).to_bytes(2,'little')
            response=await exchange(req)
            if len(response)!=63 or response[:3]!=bytes((5,3,58)):
                raise ValueError('unexpected state response '+response.hex(' '))
            return int.from_bytes(response[53:55],'little')
        async def write_once(request,stage):
            # Record intent before transmission so a timeout/error cannot result in blind retry.
            record['status']='stage_'+stage+'_attempted'
            record['writes_attempted'].append(request.hex(' '))
            save()
            response=await exchange(request)
            record['response_'+stage]=response.hex(' ')
            save()
            print('stage',stage,'response:',response.hex(' '),'echo:',response==request,flush=True)
            return response==request
        try:
            before=await read_state()
            record['before']=before;save()
            print('4561 before:',before,flush=True)
            if before!=1:
                record['status']='aborted_state_not_on';save();return
            if not await write_once(ON,'1'):
                record['status']='stage_1_no_echo_stop';save();return
            await asyncio.sleep(2)
            after_on=await read_state()
            record['after_stage_1']=after_on;save()
            print('4561 after stage 1:',after_on,flush=True)
            if after_on!=1:
                record['status']='stage_1_readback_not_1_stop';save();return
            if not await write_once(OFF,'2'):
                record['status']='stage_2_no_echo_stop';save();return
            await asyncio.sleep(2)
            after_off=await read_state()
            record['after_stage_2']=after_off
            record['status']='stage_2_readback_complete';save()
            print('4561 after stage 2:',after_off,flush=True)
        finally:
            await client.stop_notify(INDICATE_UUID)
try:
    asyncio.run(main())
except Exception as exc:
    record['error']=type(exc).__name__+': '+str(exc)
    record['status']='uncertain_failure'
    if TARGET.exists():save()
    raise
