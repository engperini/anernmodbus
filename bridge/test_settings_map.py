"""Read-only PowMr-family mapping checks against validated Anern snapshots."""
import json
import unittest
import asyncio
from pathlib import Path
from tools.rwb1_ble_protocol import crc16_modbus
from settings_map import decode_read_block, map_settings, flag_values, read_request, SETTINGS_FIELDS
from unittest.mock import patch, MagicMock
from bridge import publish_discovery, FIELDS

SNAPSHOT = Path(__file__).parent / 'fixtures/settings_read.json'

class SettingsMapTests(unittest.TestCase):
    def test_decode_full_block_from_real_snapshot(self):
        frame = next(f for f in json.loads(SNAPSHOT.read_text())['frames'] if f['start']==4536)
        words = decode_read_block(bytes.fromhex(frame['response_hex']),29)
        self.assertEqual(words[5:18],[50,220,2,245,270,284,274,240,270,60,120,30,1377])
        self.assertEqual(words[25],1)
    def test_invalid_shape_rejected_even_with_valid_crc(self):
        raw=bytes.fromhex('05 03 82');frame=raw+crc16_modbus(raw).to_bytes(2,'little')
        with self.assertRaises(ValueError):decode_read_block(frame,1)
    def test_flag_masks_from_validated_4535_read(self):
        words=decode_read_block(bytes.fromhex('05 03 02 24 01 93 44'),1)
        self.assertEqual(words,[0x124])
        flags=flag_values(words[0]);self.assertEqual(flags,{2:True,5:True,8:True})
    def test_only_allowlisted_read_requests_are_constructed(self):
        for start,count in [(4530,1),(4535,1),(4536,29)]:
            req=read_request(start,count)
            self.assertEqual(req[:2],b'\x05\x03')
            self.assertEqual(req[2:6],start.to_bytes(2,'big')+count.to_bytes(2,'big'))
            self.assertEqual(int.from_bytes(req[-2:],'little'),crc16_modbus(req[:-2]))
        with self.assertRaises(ValueError): read_request(4561,1)
    def test_discovery_has_no_command_topics_and_preserves_original_entities(self):
        messages=[]
        with patch('bridge.publish',side_effect=lambda client,topic,payload:messages.append((topic,json.loads(payload)))):
            publish_discovery(MagicMock(),'solar/test','synthetic')
        self.assertEqual(len(messages),len(FIELDS)+len(SETTINGS_FIELDS))
        self.assertTrue(all('command_topic' not in c and 'payload_press' not in c for _,c in messages))
        self.assertTrue(any(t.endswith('/pv_power/config') for t,_ in messages))
        self.assertTrue(any(t.endswith('/led_state/config') for t,_ in messages))
    def test_read_once_uses_only_four_known_read_queries(self):
        from bridge import read_once
        frames=json.loads(SNAPSHOT.read_text())['frames']
        telemetry=bytes.fromhex(next(f['response_hex'] for f in frames if f['start']==4501))
        settings=bytes.fromhex(next(f['response_hex'] for f in frames if f['start']==4536))
        def frame(word):
            body=b'\x05\x03\x02'+word.to_bytes(2,'little')
            return body+crc16_modbus(body).to_bytes(2,'little')
        replies=[telemetry,frame(0),frame(0x124),settings]
        sent=[]
        class FakeClient:
            services=MagicMock();mtu_size=247
            async def __aenter__(self):return self
            async def __aexit__(self,*_):pass
            async def start_notify(self,uuid,callback):self.notify=callback
            async def stop_notify(self,uuid):pass
            async def write_gatt_char(self,uuid,payload,response):
                sent.append(payload[3:]);self.notify(None,replies.pop(0))
        with patch('bridge.BleakScanner.find_device_by_address',return_value='fake'), \
             patch('bridge.BleakClient',return_value=FakeClient()), \
             patch('bridge.encrypt_request',side_effect=lambda request,key:request), \
             patch('bridge.decrypt_response',side_effect=lambda msg,key:msg), \
             patch('bridge.consume_fragment',side_effect=lambda data,chunks:data):
            words, values=asyncio.run(read_once('fake',b'test'))
        self.assertEqual(sent[0],bytes.fromhex('05 03 11 95 00 15 90 91'))
        self.assertEqual(sent[1:],[read_request(4530,1),read_request(4535,1),read_request(4536,29)])
        self.assertEqual(words[20],4200)
        self.assertEqual(values['led_state'],1)
    def test_only_direct_settings_and_led_are_mapped(self):
        frame=next(f for f in json.loads(SNAPSHOT.read_text())['frames'] if f['start']==4536)
        values=map_settings(decode_read_block(bytes.fromhex(frame['response_hex']),29),0x124,0)
        self.assertEqual(values['charger_priority_code'],2)
        self.assertEqual(values['output_priority_code'],1)
        self.assertEqual(values['max_charge_current'],50)
        self.assertEqual(values['bulk_charge_voltage'],28.4)
        self.assertEqual(values['led_state'],1)
        self.assertEqual(values['error_code'],0)
        self.assertEqual(values['config_bits_set'],'2,5,8')
        self.assertNotIn('temperature',values)
        self.assertNotIn('charger_status',values)
if __name__=='__main__':unittest.main()
