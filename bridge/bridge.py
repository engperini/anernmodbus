"""Read-only RWB1 BLE -> local MQTT Discovery bridge for Home Assistant Core.

Only allow-listed function-03 reads (4501/21, 4530/1, 4535/1,
4536/29) are sent. No inverter parameter writes or controls exist.
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import time

from bleak import BleakClient, BleakScanner
import paho.mqtt.client as mqtt

from tools.ble_modbus_read import (
    INDICATE_UUID, READ_REQUEST, SERVICE_UUID, WRITE_UUID,
    decrypt_response, encrypt_request,
)
from tools.rwb1_ble_protocol import consume_fragment, crc16_modbus, derive_key
from settings_map import SETTINGS_FIELDS, decode_read_block, map_settings, read_request

LOG = logging.getLogger("rwb1_bridge")
# key, Portuguese label, unit, device class, state class, multiplier, precision
FIELDS = [
    ("status", "Código de estado", None, None, None, 1, 0),
    ("grid_voltage", "Tensão da rede", "V", "voltage", "measurement", 0.1, 1),
    ("grid_frequency", "Frequência da rede", "Hz", "frequency", "measurement", 0.1, 1),
    ("pv_voltage", "Tensão solar", "V", "voltage", "measurement", 0.1, 1),
    ("pv_power", "Potência solar", "W", "power", "measurement", 1, 0),
    ("battery_voltage", "Tensão da bateria", "V", "voltage", "measurement", 0.1, 1),
    ("battery_soc", "Carga da bateria", "%", "battery", "measurement", 1, 0),
    ("battery_charge_current", "Corrente de carga da bateria", "A", "current", "measurement", 1, 0),
    ("battery_discharge_current", "Corrente de descarga da bateria", "A", "current", "measurement", 1, 0),
    ("output_voltage", "Tensão de saída", "V", "voltage", "measurement", 0.1, 1),
    ("output_frequency", "Frequência de saída", "Hz", "frequency", "measurement", 0.1, 1),
    ("load_apparent_power", "Potência aparente da carga", "VA", "apparent_power", "measurement", 1, 0),
    ("load_active_power", "Potência ativa da carga", "W", "power", "measurement", 1, 0),
    ("load_percent", "Carga do inversor", "%", None, "measurement", 1, 0),
    ("rated_power", "Potência nominal", "W", "power", "measurement", 1, 0),
]
def decode_words(frame):
    if len(frame) != 47 or frame[:3] != b"\x05\x03\x2a":
        raise ValueError("unexpected Modbus response size/function")
    if crc16_modbus(frame[:-2]) != int.from_bytes(frame[-2:], "little"):
        raise ValueError("invalid Modbus CRC")
    return [int.from_bytes(frame[3 + 2*i:5 + 2*i], "little") for i in range(21)]


async def read_once(address, key, timeout=7):
    chunks = {}
    messages = []
    received = asyncio.Event()

    def on_data(_char, data):
        message = consume_fragment(bytes(data), chunks)
        if message is not None:
            messages.append(message)
            received.set()

    device = await BleakScanner.find_device_by_address(address, timeout=8)
    if device is None:
        raise TimeoutError("RWB1 BLE not found in scan")
    async with BleakClient(device, timeout=20) as client:
        if client.services.get_service(SERVICE_UUID) is None:
            raise ValueError("expected RWB1 GATT service absent")
        await client.start_notify(INDICATE_UUID, on_data)
        max_payload = max(1, min(227, client.mtu_size - 6))

        async def query(request):
            chunks.clear()
            messages.clear()
            received.clear()
            encrypted = encrypt_request(request, key)
            fragments = [encrypted[i:i + max_payload] for i in range(0, len(encrypted), max_payload)]
            for index, payload in enumerate(fragments, 1):
                await client.write_gatt_char(
                    WRITE_UUID, bytes((index, len(fragments), len(payload))) + payload, response=True
                )
            await asyncio.wait_for(received.wait(), timeout=timeout)
            return decrypt_response(messages[-1], key)

        try:
            words = decode_words(await query(READ_REQUEST))
            try:
                error = decode_read_block(await query(read_request(4530, 1)), 1)[0]
                flags = decode_read_block(await query(read_request(4535, 1)), 1)[0]
                settings = decode_read_block(await query(read_request(4536, 29)), 29)
                extra = map_settings(settings, flags, error)
            except Exception as exc:
                LOG.warning("Optional settings read failed (telemetry retained): %s", exc)
                extra = {}
        finally:
            await client.stop_notify(INDICATE_UUID)
    return words, extra


def publish(client, topic, payload, retain=True):
    info = client.publish(topic, payload, qos=1, retain=retain)
    info.wait_for_publish(timeout=5)
    if not info.is_published():
        raise TimeoutError("MQTT publish timed out")


def publish_discovery(client, base, device_id):
    device = {
        "identifiers": ["rwb1_ble_" + device_id],
        "name": "Inversor solar Anern",
        "manufacturer": "Anern",
        "model": "AN-SCI-ECO-4200 / Solar Plug RWB1",
    }
    for fields, diagnostic in ((FIELDS, False), (SETTINGS_FIELDS, True)):
      for key, name, unit, dclass, sclass, _factor, _precision in fields:
        config = {
            "name": name,
            "unique_id": f"rwb1_ble_{device_id}_{key}",
            "state_topic": f"{base}/state",
            "value_template": "{{ value_json." + key + " }}",
            "availability_topic": f"{base}/availability",
            "device": device,
        }
        if diagnostic:
            config["entity_category"] = "diagnostic"
        if unit is not None:
            config["unit_of_measurement"] = unit
        if dclass is not None:
            config["device_class"] = dclass
        if sclass is not None:
            config["state_class"] = sclass
        publish(client, f"homeassistant/sensor/rwb1_ble_{device_id}/{key}/config", json.dumps(config))


def map_words(words):
    values = {key: round(words[i] * factor, precision)
              for i, (key, _name, _unit, _dc, _sc, factor, precision) in enumerate(FIELDS[:14])}
    values["rated_power"] = words[20]
    return values


async def run(args):
    dtu_id = os.environ.get("RWB1_DTU_ID")
    address = os.environ.get("RWB1_BLE_ADDRESS")
    if not dtu_id or not address:
        raise ValueError("RWB1_DTU_ID and RWB1_BLE_ADDRESS must be set")
    key = derive_key(dtu_id)
    device_id = hashlib.sha256(dtu_id.encode()).hexdigest()[:12]
    base = f"solar/rwb1_ble/{device_id}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="rwb1-ble-" + device_id)
    client.will_set(base + "/availability", "offline", qos=1, retain=True)
    client.connect("127.0.0.1", 1883, keepalive=60)
    client.loop_start()
    try:
        publish_discovery(client, base, device_id)
        while True:
            started = time.monotonic()
            try:
                words, settings_values = await read_once(address, key)
                values = map_words(words)
                values.update(settings_values)
                publish(client, base + "/state", json.dumps(values))
                publish(client, base + "/availability", "online")
                LOG.info("CRC valid; PV=%s W, battery=%s V, rated=%s W",
                         values["pv_power"], values["battery_voltage"], values["rated_power"])
            except Exception as exc:
                LOG.warning("BLE read failed: %s", exc)
                publish(client, base + "/availability", "offline")
                if args.once:
                    raise
            if args.once:
                return
            await asyncio.sleep(max(0, args.interval - (time.monotonic() - started)))
    finally:
        publish(client, base + "/availability", "offline")
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="single BLE read + MQTT publish")
    parser.add_argument("--interval", type=int, default=30)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run(arguments))
