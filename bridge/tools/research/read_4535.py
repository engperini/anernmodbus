import asyncio,os,sys
from pathlib import Path
from bleak import BleakClient,BleakScanner
sys.path.insert(0,'/home/pi/solar-rwb1-ble')
from tools.ble_modbus_read import SERVICE_UUID,WRITE_UUID,INDICATE_UUID,encrypt_request,decrypt_response
from tools.rwb1_ble_protocol import consume_fragment,crc16_modbus,derive_key
e=dict(l.split('=',1) for l in Path('/home/pi/solar-rwb1-ble/rwb1.env').read_text().splitlines() if '=' in l and not l.lstrip().startswith('#'))
async def run():
 device=await BleakScanner.find_device_by_address(e['RWB1_BLE_ADDRESS'].strip().strip('"\''),timeout=10)
 assert device is not None
 key=derive_key(e['RWB1_DTU_ID'].strip().strip('"\''));chunks={};messages=[];ready=asyncio.Event()
 def cb(_,d):
  r=consume_fragment(bytes(d),chunks)
  if r is not None:messages.append(r);ready.set()
 req=bytes.fromhex('05 03 11 b7 00 01');req+=crc16_modbus(req).to_bytes(2,'little')
 async with BleakClient(device,timeout=20) as client:
  assert client.services.get_service(SERVICE_UUID)
  await client.start_notify(INDICATE_UUID,cb)
  try:
   enc=encrypt_request(req,key);n=max(1,min(227,client.mtu_size-6));parts=[enc[i:i+n] for i in range(0,len(enc),n)]
   for i,p in enumerate(parts,1):await client.write_gatt_char(WRITE_UUID,bytes((i,len(parts),len(p)))+p,response=True)
   await asyncio.wait_for(ready.wait(),timeout=10)
  finally:await client.stop_notify(INDICATE_UUID)
 rsp=decrypt_response(messages[-1],key)
 assert crc16_modbus(rsp[:-2])==int.from_bytes(rsp[-2:],'little')
 print('4535 request:',req.hex(' '),'response:',rsp.hex(' '))
 if len(rsp)==7 and rsp[:3]==b'\x05\x03\x02':print('4535 little-endian:',int.from_bytes(rsp[3:5],'little'),'big-endian:',int.from_bytes(rsp[3:5],'big'))
asyncio.run(run())
