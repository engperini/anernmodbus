"""RWB1 BLE <-> MQTT bridge for the Anern AN-SCI-ECO-4200 (Home Assistant discovery).

- Reads the whole block 4501-4564 (FC03) every --interval seconds.
- Publishes telemetry, decoded texts/flags and the current value of every setting.
- Exposes the settings as MQTT select/number/switch/button entities.
- Writes only on an explicit user command, one at a time, with the safe flow of
  docs/02: fresh read -> validate (range + rules) -> one FC06 -> identical echo ->
  re-read and compare -> publish result. A refusal is never retried.
- Writes are accepted only while the Home Assistant locks are on (topic <base>/locks,
  published by the HA package): "edit" for groups A, B and D; "edit" + "critical"
  for group C, whose select only prepares the value and a button applies it.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from bleak import BleakClient, BleakScanner

from anern_map import (
    BLOCK_COUNT, BLOCK_START, CONTROLS, Control, WriteRefused, check_write_echo,
    SOC_RANGES, decode_block, decode_read, encode_soc, read_request, required_locks, soc_mode,
    validate_rules, validate_soc_rules, write_request,
)
from tools.ble_modbus_read import INDICATE_UUID, SERVICE_UUID, WRITE_UUID, decrypt_response, encrypt_request
from tools.rwb1_ble_protocol import consume_fragment, derive_key

LOG = logging.getLogger("rwb1_bridge")
HERE = Path(__file__).resolve().parent
WRITE_LOG = Path(os.environ.get("RWB1_WRITE_LOG", HERE / "writes.log"))
LOCKS_TOPIC = "solar/rwb1_ble/locks"   # fixed topic used by the HA package
PENDING_TTL = 120          # s: a prepared group C value expires
BT_RESET_AFTER = 5         # consecutive failures before resetting the adapter

DEVICE = {
    "name": "Anern solar inverter",
    "manufacturer": "Anern",
    "model": "AN-SCI-ECO-4200 / Solar Plug RWB1",
}

# key, name, unit, device_class, state_class, precision, icon, diagnostic
SENSORS = [
    ("operation_mode", "Operation mode", None, None, None, None, "mdi:state-machine", False),
    ("status", "Operation mode code (4501)", None, None, None, 0, None, True),
    ("pv_voltage", "PV voltage", "V", "voltage", "measurement", 1, None, False),
    ("pv_power", "PV power", "W", "power", "measurement", 0, None, False),
    ("battery_voltage", "Battery voltage", "V", "voltage", "measurement", 1, None, False),
    ("battery_soc", "Battery SOC (BMS)", "%", "battery", "measurement", 0, None, False),
    ("battery_charge_current", "Battery charge current", "A", "current", "measurement", 0, None, False),
    ("battery_discharge_current", "Battery discharge current", "A", "current", "measurement", 0, None, False),
    ("grid_voltage", "Grid voltage", "V", "voltage", "measurement", 1, None, False),
    ("grid_frequency", "Grid frequency", "Hz", "frequency", "measurement", 1, None, False),
    ("output_voltage", "Output voltage", "V", "voltage", "measurement", 1, None, False),
    ("output_frequency", "Output frequency", "Hz", "frequency", "measurement", 1, None, False),
    ("load_active_power", "Load active power", "W", "power", "measurement", 0, None, False),
    ("load_apparent_power", "Load apparent power", "VA", "apparent_power", "measurement", 0, None, False),
    ("load_percent", "Load", "%", None, "measurement", 0, "mdi:gauge", False),
    ("ntc_temperature", "NTC temperature", "°C", "temperature", "measurement", 0, None, False),
    ("led_text", "LED (39) · read only", None, None, None, None, "mdi:led-on", False),
    ("led_state", "LED (4561)", None, None, None, 0, None, True),
    ("fault_text", "Fault", None, None, None, None, "mdi:alert-octagon", False),
    ("fault_code", "Fault code (4530)", None, None, None, 0, None, True),
    ("warning_text", "Warning", None, None, None, None, "mdi:alert", False),
    ("warning_code", "Warning code (4529)", None, None, None, 0, None, True),
    ("dual_cutoff_voltage", "Dual output cutoff (42) · V", "V", "voltage", None, 1, None, False),
    ("dual_cutoff_percent", "Dual output cutoff (42) · %", "%", None, None, 0, "mdi:percent", False),
    ("cpu_version", "CPU version", None, None, None, None, "mdi:chip", False),
    ("rated_power", "Rated power", "W", "power", None, 0, None, False),
    ("rated_apparent_power", "Rated apparent power", "VA", "apparent_power", None, 0, None, False),
    ("rated_ac_voltage", "Rated AC voltage", "V", "voltage", None, 0, None, False),
    ("rated_ac_current", "Rated AC current", "A", "current", None, 0, None, False),
    ("rated_battery_voltage", "Rated battery voltage", "V", "voltage", None, 1, None, False),
    ("rated_output_voltage", "Rated output voltage", "V", "voltage", None, 0, None, False),
    ("rated_frequency", "Rated frequency", "Hz", "frequency", None, 1, None, False),
    ("rated_output_current", "Rated output current", "A", "current", None, 0, None, False),
    ("config_flags", "Configuration flags (4535)", None, None, None, 0, None, True),
    ("status_flags", "Status flags (4553)", None, None, None, 0, None, True),
]

BINARY_SENSORS = [
    ("charge_enabled", "Charging enabled", None, "mdi:battery-plus"),
    ("grid_active", "Grid active", "power", None),
    ("on_battery", "On battery", None, "mdi:home-battery"),
    ("equalization", "Equalization (30) · read only", None, "mdi:scale-balance"),
    ("equalization_now", "Equalize now (36) · read only", None, "mdi:scale-balance"),
]

# Discovery keys of the 2026-11-13 bridge that are now controls or renamed: removed from HA.
OBSOLETE_SENSORS = [
    "charger_priority_code", "output_priority_code", "input_range_code", "battery_type_code",
    "frequency_mode_code", "max_charge_current", "max_grid_charge_current", "low_battery_warning",
    "low_battery_shutdown", "bulk_charge_voltage", "float_charge_voltage", "back_to_grid_voltage",
    "back_to_battery_voltage", "error_code", "config_flags_raw", "config_bits_set",
]


class RWB1Session:
    """One BLE connection to the dongle; Modbus frames in, Modbus frames out."""

    def __init__(self, address: str, key: bytes, timeout: float = 10):
        self.address, self.key, self.timeout = address, key, timeout
        self.client: Optional[BleakClient] = None
        self._chunks: Dict[int, bytes] = {}
        self._messages: list = []
        self._received = asyncio.Event()

    def _on_data(self, _char, data) -> None:
        message = consume_fragment(bytes(data), self._chunks)
        if message is not None:
            self._messages.append(message)
            self._received.set()

    async def __aenter__(self):
        device = await BleakScanner.find_device_by_address(self.address, timeout=10)
        if device is None:
            # A dongle left connected by a killed process stops advertising: drop that link.
            await asyncio.to_thread(subprocess.run, ["bluetoothctl", "disconnect", self.address],
                                    capture_output=True, timeout=15)
            device = await BleakScanner.find_device_by_address(self.address, timeout=10)
        if device is None:
            raise TimeoutError("RWB1 dongle not found in BLE scan")
        self.client = BleakClient(device, timeout=20)
        await self.client.connect()
        if self.client.services.get_service(SERVICE_UUID) is None:
            raise ValueError("RWB1 GATT service not found")
        await self.client.start_notify(INDICATE_UUID, self._on_data)
        return self

    async def __aexit__(self, *_exc):
        # BlueZ on Debian 13 may drop the D-Bus link during teardown: never fatal.
        for step in (lambda: self.client.stop_notify(INDICATE_UUID), lambda: self.client.disconnect()):
            try:
                await step()
            except Exception as exc:  # noqa: BLE001
                LOG.debug("BLE teardown: %r", exc)
        return False

    async def query(self, request: bytes) -> bytes:
        self._chunks.clear()
        self._messages.clear()
        self._received.clear()
        encrypted = encrypt_request(request, self.key)
        size = max(1, min(227, self.client.mtu_size - 6))
        parts = [encrypted[i:i + size] for i in range(0, len(encrypted), size)]
        for index, payload in enumerate(parts, 1):
            await self.client.write_gatt_char(WRITE_UUID, bytes((index, len(parts), len(payload))) + payload, response=True)
        await asyncio.wait_for(self._received.wait(), timeout=self.timeout)
        return decrypt_response(self._messages[-1], self.key)

    async def read_block(self):
        return decode_read(await self.query(read_request()), BLOCK_COUNT)


def load_env_file(path: Path = HERE / "rwb1.env") -> None:
    """Read KEY=VALUE lines (like systemd EnvironmentFile) without overriding the environment."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


async def scan(prefix: str = "SSL_", timeout: float = 10.0) -> list:
    """Nearby RWB1 dongles (they advertise as SSL_...): [(address, name, rssi)]."""
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    return sorted(
        ((dev.address, adv.local_name, adv.rssi) for dev, adv in found.values()
         if (adv.local_name or "").startswith(prefix)),
        key=lambda item: -(item[2] or -999),
    )


class Bridge:
    def __init__(self, args):
        self.args = args
        self.dtu_id = os.environ.get("RWB1_DTU_ID", "").strip()
        if not self.dtu_id:
            raise SystemExit("RWB1_DTU_ID is not set (rwb1.env). See the README: 'Finding the DTU ID'.")
        self.address = os.environ.get("RWB1_BLE_ADDRESS", "").strip()
        self.key = derive_key(self.dtu_id)
        self.device_id = hashlib.sha256(self.dtu_id.encode()).hexdigest()[:12]
        self.base = f"solar/rwb1_ble/{self.device_id}"
        self.device = dict(DEVICE, identifiers=["rwb1_ble_" + self.device_id])
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.wake = asyncio.Event()
        self.commands: asyncio.Queue = asyncio.Queue()
        self.locks = {"edit": False, "critical": False}
        self.pending: Dict[str, tuple] = {}         # group C key -> (value, expires_at)
        self.values: Dict[str, Any] = {}
        self.failures = 0
        self.mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="rwb1-ble-" + self.device_id)
        self.mqtt.will_set(self.base + "/availability", "offline", qos=1, retain=True)
        user = os.environ.get("MQTT_USER") or os.environ.get("MQTT_USERNAME")
        if user:
            self.mqtt.username_pw_set(user, os.environ.get("MQTT_PASSWORD", ""))
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_message = self._on_message

    # ------------------------------------------------------------ MQTT
    def publish(self, topic: str, payload: Any, retain: bool = True) -> None:
        if not isinstance(payload, (str, bytes)):
            payload = json.dumps(payload, ensure_ascii=False)
        self.mqtt.publish(topic, payload, qos=1, retain=retain)

    def _on_connect(self, client, _userdata, _flags, _rc, _props=None):
        client.subscribe([(self.base + "/set/+", 1), (self.base + "/apply/+", 1),
                          (self.base + "/locks", 1), (LOCKS_TOPIC, 1), ("homeassistant/status", 1)])
        self.publish_discovery()

    def _on_message(self, _client, _userdata, msg):
        payload = msg.payload.decode("utf-8", "replace").strip()
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.handle_message, msg.topic, payload)

    def handle_message(self, topic: str, payload: str) -> None:
        if topic == "homeassistant/status":
            if payload == "online":
                LOG.info("HA online: re-sending discovery and state")
                self.publish_discovery()
                self.publish_state()
            return
        if topic in (self.base + "/locks", LOCKS_TOPIC):
            try:
                data = json.loads(payload)
                self.locks = {"edit": bool(data.get("edit")), "critical": bool(data.get("critical"))}
            except ValueError:
                self.locks = {"edit": False, "critical": False}
            LOG.info("locks: %s", self.locks)
            return
        action, key = topic.rsplit("/", 2)[-2:]
        control = CONTROLS.get(key)
        if control is None:
            return
        if action == "set" and control.group == "C":
            self.pending[key] = (payload, time.monotonic() + PENDING_TTL)
            self.result(f"{control.name}: {payload} prepared — press Apply (expires in 2 min)")
            self.publish_state()
        elif action == "set":
            self.commands.put_nowait((key, payload))
            self.wake.set()
        elif action == "apply":
            pending = self.pending.pop(key, None)
            if pending is None or pending[1] < time.monotonic():
                self.result(f"{control.name}: nothing prepared to apply")
                self.publish_state()
                return
            self.commands.put_nowait((key, pending[0]))
            self.wake.set()

    def result(self, text: str) -> None:
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        LOG.info("result: %s", text)
        self.publish(self.base + "/result", f"{stamp} · {text}"[:250])

    def publish_state(self) -> None:
        if not self.values:
            return
        now = time.monotonic()
        state = dict(self.values)
        for key, (value, expires) in list(self.pending.items()):
            if expires < now:
                del self.pending[key]
            else:
                state[key] = value
        self.publish(self.base + "/state", state)

    def _entity(self, component: str, key: str, name: str, **extra) -> None:
        config = {
            "name": name,
            "unique_id": f"rwb1_ble_{self.device_id}_{key}",
            "default_entity_id": f"{component}.anern_{key}",
            "availability_topic": self.base + "/availability",
            "device": self.device,
        }
        config.update({k: v for k, v in extra.items() if v is not None})
        self.publish(f"homeassistant/{component}/rwb1_ble_{self.device_id}/{key}/config", config)

    def publish_discovery(self) -> None:
        state = self.base + "/state"
        for key in OBSOLETE_SENSORS:
            self.publish(f"homeassistant/sensor/rwb1_ble_{self.device_id}/{key}/config", "")
        for key, name, unit, dclass, sclass, precision, icon, diagnostic in SENSORS:
            self._entity("sensor", key, name, state_topic=state,
                         value_template="{{ value_json.%s }}" % key,
                         unit_of_measurement=unit, device_class=dclass, state_class=sclass,
                         suggested_display_precision=precision, icon=icon,
                         entity_category="diagnostic" if diagnostic else None)
        self._entity("sensor", "last_read", "Last read", state_topic=state,
                     value_template="{{ value_json.last_read }}", device_class="timestamp",
                     entity_category="diagnostic")
        self._entity("sensor", "last_result", "Last setting result",
                     state_topic=self.base + "/result", icon="mdi:clipboard-text-clock")
        for key, name, dclass, icon in BINARY_SENSORS:
            self._entity("binary_sensor", key, name, state_topic=state,
                         value_template="{{ value_json.%s }}" % key,
                         payload_on="ON", payload_off="OFF", device_class=dclass, icon=icon)
        for control in CONTROLS.values():
            self._control_discovery(control, state)

    def _control_discovery(self, c: Control, state: str) -> None:
        command = f"{self.base}/set/{c.key}"
        template = "{{ value_json.%s }}" % c.key
        if c.kind == "select":
            self._entity("select", c.key, c.name, state_topic=state, value_template=template,
                         command_topic=command, options=list(c.options), icon=c.icon or "mdi:format-list-bulleted")
        elif c.kind == "number" and c.scale != 1:
            # Voltages as MQTT text so the box keeps one decimal ("27.0"); a number entity
            # in box mode drops it ("27"). The bridge still validates range and step.
            self.publish(f"homeassistant/number/rwb1_ble_{self.device_id}/{c.key}/config", "")
            soc = c.key in SOC_RANGES
            self._entity("text", c.key, f"{c.name} [{'V or %' if soc else 'V'}]", state_topic=state,
                         value_template="{{ value_json.%s_display }}" % c.key,
                         command_topic=command, mode="text", min=1, max=5,
                         pattern=r"^\d{1,3}([.,]\d)?%?$" if soc else r"^\d{1,2}([.,]\d)?$",
                         icon=c.icon or "mdi:tune-vertical")
        elif c.kind == "number":
            self._entity("number", c.key, c.name, state_topic=state, value_template=template,
                         command_topic=command, min=c.minimum, max=c.maximum, step=c.step,
                         unit_of_measurement=c.unit, mode="box", icon=c.icon or "mdi:tune-vertical")
        else:
            self._entity("switch", c.key, c.name, state_topic=state, value_template=template,
                         command_topic=command, payload_on="ON", payload_off="OFF",
                         state_on="ON", state_off="OFF", icon="mdi:toggle-switch-outline")
        if c.group == "C":
            self._entity("button", c.key + "_apply", f"Apply {c.name}",
                         command_topic=f"{self.base}/apply/{c.key}", payload_press="PRESS",
                         icon="mdi:check-bold")

    # ------------------------------------------------------------ cycle
    def _publish_values(self, words) -> None:
        self.values = decode_block(words)
        self.values["last_read"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        self.publish_state()
        self.publish(self.base + "/availability", "online")

    async def _execute(self, session: RWB1Session, key: str, value: str) -> None:
        control = CONTROLS[key]
        missing = [lock for lock in required_locks(control) if not self.locks.get(lock)]
        if missing:
            names = {"edit": "Edit mode", "critical": "Critical settings"}
            self.result(f"{control.name}: blocked — turn on {' and '.join(names[m] for m in missing)}")
            self.publish_state()            # snap the UI back to the read value
            return
        words = await session.read_block()
        self._publish_values(words)
        old = self.values.get(key + "_display", self.values.get(key))
        if control.kind == "number":
            value = value.replace(",", ".")
        try:
            if key in SOC_RANGES and soc_mode(self.values):
                # Tested 2026-11-15: 5025 refused 30 (%) with exception 3 (illegal value);
                # it only takes volts. The % register is still unknown (docs/10).
                raise ValueError("in BMS mode the inverter keeps this setting in %, in a register "
                                 "not found yet; change it on the inverter display for now")
            else:
                raw = control.encode(value)
                if control.group == "B":
                    validate_rules(self.values, key, value)
        except ValueError as exc:
            self.result(f"{control.name}: {exc} (not sent)")
            self.publish_state()
            return
        request = write_request(control.write_register, raw)
        entry = {"time": dt.datetime.now().isoformat(timespec="seconds"), "key": key,
                 "register": control.write_register, "old": old, "new": value, "raw": raw}
        try:
            check_write_echo(request, await session.query(request))
            await asyncio.sleep(1.5)
            self._publish_values(await session.read_block())
            now = self.values.get(key)
            if key in SOC_RANGES and soc_mode(self.values):
                now = self.values[key + "_display"]
                same = self.values[key + "_raw"] == raw
            else:
                same = (str(now) == str(value)) or (control.kind == "number" and abs(float(now) - float(value)) < 1e-6)
            entry["result"] = "ok" if same else f"echo ok, re-read {now}"
            self.result(f"{control.name}: {old} → {value} · " + ("OK, verified" if same else f"echo OK but re-read {now}"))
        except WriteRefused as exc:
            entry["result"] = f"refused: {exc}"
            self.result(f"{control.name}: {exc} — will not be retried")
        except Exception as exc:  # noqa: BLE001
            entry["result"] = f"error: {exc!r}"
            self.result(f"{control.name}: error ({exc.__class__.__name__}) — not retried; check the inverter display")
        with WRITE_LOG.open("a", encoding="utf-8") as log:
            log.write(json.dumps(entry, ensure_ascii=False) + "\n")

    async def cycle(self) -> None:
        async with RWB1Session(self.address, self.key) as session:
            self._publish_values(await session.read_block())
            while not self.commands.empty():
                key, value = self.commands.get_nowait()
                await self._execute(session, key, value)
        self.failures = 0
        v = self.values
        LOG.info("read OK: mode=%s PV=%s W battery=%s V %s%%", v["operation_mode"], v["pv_power"],
                 v["battery_voltage"], v["battery_soc"])

    def reset_bluetooth(self) -> None:
        LOG.warning("%d failures in a row: resetting the Bluetooth adapter", self.failures)
        for cmd in (["bluetoothctl", "disconnect", self.address], ["bluetoothctl", "power", "off"],
                    ["bluetoothctl", "power", "on"]):
            try:
                subprocess.run(cmd, capture_output=True, timeout=15)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("bluetoothctl failed: %r", exc)
            time.sleep(2)

    async def run(self) -> None:
        self.loop = asyncio.get_running_loop()
        if not self.address:
            found = await scan()
            if len(found) != 1:
                raise SystemExit(f"RWB1_BLE_ADDRESS is not set and {len(found)} SSL_ dongles were found; "
                                 "run: bridge.py --scan and put the address in rwb1.env")
            self.address = found[0][0]
            LOG.info("dongle found by scan: %s (%s)", found[0][1], self.address)
        self.mqtt.connect(self.args.mqtt_host, self.args.mqtt_port, keepalive=60)
        self.mqtt.loop_start()
        try:
            while True:
                started = time.monotonic()
                self.wake.clear()
                try:
                    await self.cycle()
                except Exception as exc:  # noqa: BLE001
                    self.failures += 1
                    LOG.warning("BLE read failed (%d): %r", self.failures, exc)
                    if self.failures >= 3:
                        self.publish(self.base + "/availability", "offline")
                    if self.failures % BT_RESET_AFTER == 0:
                        await asyncio.to_thread(self.reset_bluetooth)
                    if not self.commands.empty():
                        while not self.commands.empty():
                            key, _value = self.commands.get_nowait()
                            self.result(f"{CONTROLS[key].name}: not sent (no BLE connection) — try again")
                    if self.args.once:
                        raise
                if self.args.once:
                    return
                delay = self.args.interval if self.failures == 0 else min(300, self.args.interval * 2 ** min(self.failures, 4))
                try:
                    await asyncio.wait_for(self.wake.wait(), timeout=max(0, delay - (time.monotonic() - started)))
                except asyncio.TimeoutError:
                    pass
        finally:
            self.publish(self.base + "/availability", "offline")
            self.mqtt.loop_stop()
            self.mqtt.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="one read + publish, then exit")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--mqtt-host", default=os.environ.get("MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--mqtt-port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    parser.add_argument("--scan", action="store_true", help="list nearby RWB1 dongles (SSL_...) and exit")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    load_env_file()
    if args.scan:
        found = asyncio.run(scan())
        if not found:
            print("No SSL_ dongle found. Is the inverter on and the phone app disconnected?")
        for address, name, rssi in found:
            print(f"{address}  {name}  RSSI {rssi} dBm")
        return
    args.mqtt_host = os.environ.get("MQTT_HOST", args.mqtt_host)
    args.mqtt_port = int(os.environ.get("MQTT_PORT", args.mqtt_port))
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("bleak").setLevel(logging.WARNING)
    asyncio.run(Bridge(args).run())


if __name__ == "__main__":
    main()
