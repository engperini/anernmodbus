"""Owner-authorized strictly bounded function-10 LED test; no other write addresses/values."""
import asyncio,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from bleak import BleakClient,BleakScanner
sys.path.insert(0,'/home/pi/solar-rwb1-ble')
from tools.ble_modbus_read import SERVICE_UUID,WRITE_UUID,INDICATE_UUID,encrypt_request,decrypt_response
from tools.rwb1_ble_protocol import crc16_modbus,consume_fragment,derive_key
BASE=Path('/home/pi/.config/siseli/led-snapshots')
TARGET=BASE/'write_test_f10.json'
assert not TARGET.exists(),'already attempted; refusing to repeat'
FRAMES={
 'A_ON':bytes.fromhex('05 10 11 D1 00 01 02 00 01 46 10'),
 'A_ACK':bytes.fromhex('05 10 11 D1 00 01 55 48'),
 'B_ON':bytes.fromhex('05 10 13 B2 00 01 02 00 01 6C 43'),
 'B_ACK':bytes.fromhex('05 10 13 B2 00 01 A4 EE'),
 'A_OFF':bytes.fromhex('05 10 11 D1 00 01 02 00 00 87 D0'),
 'B_OFF':bytes.fromhex('05 10 13 B2 00 01 02 00 00 AD 83'),
}
assert all(crc16_modbus(f[:-2])==int.from_bytes(f[-2:],'little') for f in FRAMES.values())
env=dict(line.strip().split('=',1) for line in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
address=env['RWB1_BLE_ADDRESS'].strip().strip('"\'')
key=derive_key(env['RWB1_DTU_ID'].strip().strip('"\''))
rec={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status':'initialized','writes_attempted':[]}
def save():
 if TARGET.exists():TARGET.write_text(json.dumps(rec,indent=2))
 else:
  with TARGET.open('x') as f:json.dump(rec,f,indent=2)
 os.chmod(TARGET,0o600)
async def main():
 device=await BleakScanner.find_device_by_address(address,timeout=12)
 if device is None:raise RuntimeError('BLE logger absent; no writes attempted')
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
   assert crc16_modbus(response[:-2])==int.from_bytes(response[-2:],'little'),'bad CRC'
   return response
  async def read_state():
   request=bytes.fromhex('05 03 11 B8 00 1D 01 5E')
   response=await exchange(request)
   assert len(response)==63 and response[:3]==bytes((5,3,58)),'invalid 4536 response'
   return int.from_bytes(response[53:55],'little')
  async def send_once(label):
   frame=FRAMES[label]
   rec['writes_attempted'].append(label)
   rec['status']='attempted_'+label
   save()  # durably record intent before side effect; never retry after uncertainty
   print('sending',label,frame.hex(' '),flush=True)
   response=await exchange(frame)
   rec['response_'+label]=response.hex(' ');save()
   print('response',label,response.hex(' '),flush=True)
   return response
  try:
   rec['before']=await read_state();save()
   print('4561 before:',rec['before'],flush=True)
   if rec['before']!=1:
    rec['status']='abort_not_on';save();return
   response=await send_once('A_ON')
   if response==FRAMES['A_ACK']:
    selected='A'
   elif len(response)==5 and response[:2]==bytes.fromhex('05 90'):
    selected='B'
    print('A function-10 error; proceeding to authorized B',flush=True)
    response=await send_once('B_ON')
    if response!=FRAMES['B_ACK']:
     rec['status']='stop_B_not_success';save();return
   else:
    rec['status']='stop_A_unexpected';save();return
   rec['accepted_address']=4561 if selected=='A' else 5042
   await asyncio.sleep(2)
   rec['after_on']=await read_state();save()
   print('4561 after ON no-op:',rec['after_on'],flush=True)
   if rec['after_on']!=1:
    rec['status']='stop_state_changed_after_on';save();return
   response=await send_once(selected+'_OFF')
   if response!=FRAMES[selected+'_ACK']:
    rec['status']='stop_off_not_success';save();return
   await asyncio.sleep(2)
   rec['after_off']=await read_state()
   rec['status']='off_ack_and_readback';save()
   print('4561 after OFF:',rec['after_off'],flush=True)
  finally:
   await client.stop_notify(INDICATE_UUID)
try:asyncio.run(main())
except Exception as exc:
 rec['status']='uncertain_failure';rec['error']=type(exc).__name__+': '+str(exc)
 if TARGET.exists():save()
 raise
