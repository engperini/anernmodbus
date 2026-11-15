"""Decoding, frames, validation and write safety (no BLE, no inverter writes)."""
import asyncio
import csv
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from anern_map import (
    BLOCK_COUNT, CONTROLS, WriteRefused, check_write_echo, decode_block, decode_read,
    read_request, swap16, validate_rules, write_request,
)
from tools.rwb1_ble_protocol import crc16_modbus

DUMP = Path(__file__).resolve().parent.parent / "data" / "dump-2026-11-14-1127.csv"


def dump_words():
    with DUMP.open() as f:
        rows = {int(r["registrador"]): int(r["valor_bruto"]) for r in csv.DictReader(f)}
    return [rows[r] for r in range(4501, 4565)]


def frame_for(words):
    body = bytes((5, 3, 2 * len(words))) + b"".join(w.to_bytes(2, "little") for w in words)
    return body + crc16_modbus(body).to_bytes(2, "little")


class DecodeTests(unittest.TestCase):
    def setUp(self):
        self.v = decode_block(dump_words())

    def test_block_frame_roundtrip(self):
        words = dump_words()
        self.assertEqual(decode_read(frame_for(words), BLOCK_COUNT), words)
        with self.assertRaises(ValueError):
            decode_read(frame_for(words)[:-1] + b"\x00", BLOCK_COUNT)

    def test_telemetry_scaling(self):
        v = self.v
        self.assertEqual((v["grid_voltage"], v["grid_frequency"], v["pv_voltage"]), (217.8, 60.0, 161.7))
        self.assertEqual((v["pv_power"], v["battery_voltage"], v["battery_soc"]), (253, 26.7, 34))
        self.assertEqual((v["load_apparent_power"], v["load_active_power"], v["load_percent"]), (348, 248, 8))
        self.assertEqual((v["dual_cutoff_voltage"], v["dual_cutoff_percent"]), (22.0, 55))
        self.assertEqual((v["rated_power"], v["rated_battery_voltage"], v["rated_frequency"]), (4200, 24.0, 50.0))
        self.assertEqual(v["ntc_temperature"], 40)

    def test_texts(self):
        self.assertEqual(self.v["operation_mode"], "Line mode (bypass)")
        self.assertIn("4554=2", self.v["unknown_registers"])
        self.assertEqual(self.v["cpu_version"], "U1 75 11")
        self.assertEqual(self.v["fault_text"], "No fault")
        self.assertEqual(self.v["led_text"], "LOF (off)")

    def test_swapped_config_flags_match_display(self):
        self.assertEqual(swap16(292), 0x2401)
        v = self.v
        on = {k for k in ("fault_record", "backlight", "beep_source_loss") if v[k] == "ON"}
        self.assertEqual(on, {"fault_record", "backlight", "beep_source_loss"})
        for k in ("alarm", "restart_overload", "restart_overtemp", "default_screen", "overload_bypass",
                  "equalization", "equalization_now"):
            self.assertEqual(v[k], "OFF", k)

    def test_status_flags(self):
        self.assertEqual(swap16(5478), 0x6615)
        self.assertEqual((self.v["charge_enabled"], self.v["grid_active"], self.v["on_battery"]), ("ON", "ON", "OFF"))

    def test_settings_read_values(self):
        v = self.v
        self.assertEqual((v["charger_source"], v["output_source"]), ("OSO", "SBU"))
        self.assertEqual((v["ac_input_range"], v["battery_type"]), ("UPS", "LIL"))
        self.assertEqual((v["output_frequency_setting"], v["output_voltage_setting"]), ("60 Hz", "220 V"))
        self.assertEqual((v["total_charge_current"], v["grid_charge_current"]), (40, 2))
        self.assertEqual((v["back_to_grid"], v["back_to_battery"], v["bulk_voltage"]), (24.5, 27.0, 28.4))
        self.assertEqual((v["float_voltage"], v["low_cutoff"], v["equalization_voltage"]), (27.4, 24.0, 27.0))
        self.assertEqual((v["equalization_time"], v["equalization_timeout"], v["equalization_interval"]), (60, 120, 30))


class SocModeTests(unittest.TestCase):
    def test_soc_mode_ranges_from_manual(self):
        from anern_map import encode_soc
        self.assertEqual(encode_soc("back_to_grid", "30%"), 30)
        self.assertEqual(encode_soc("back_to_battery", "60"), 60)
        self.assertEqual(encode_soc("low_cutoff", "20 %"), 20)
        for key, bad in [("back_to_grid", "55"), ("back_to_grid", "32"), ("back_to_battery", "25"),
                         ("low_cutoff", "31"), ("low_cutoff", "4"), ("back_to_grid", "30.5")]:
            with self.assertRaises(ValueError, msg=f"{key}={bad}"):
                encode_soc(key, bad)

    def test_display_volts_or_percent(self):
        from anern_map import setting_display
        v = decode_block(dump_words())                       # battery type LIL
        self.assertEqual(v["back_to_grid_display"], "24.5")  # register still holds volts
        self.assertEqual(setting_display(v, "back_to_grid", 30), "30%")
        self.assertEqual(setting_display(dict(v, battery_type="AGM"), "back_to_grid", 245), "24.5")
        self.assertEqual(v["bulk_voltage_display"], "28.4")

    def test_soc_rules(self):
        from anern_map import validate_soc_rules
        validate_soc_rules({"back_to_grid": 30, "back_to_battery": 60, "low_cutoff": 20}, "back_to_grid", 35)
        with self.assertRaises(ValueError):
            validate_soc_rules({"back_to_grid": 30, "back_to_battery": 60, "low_cutoff": 20}, "back_to_grid", 60)
        # current values still in volts: % rules are not applied
        validate_soc_rules({"back_to_grid": 245, "back_to_battery": 270, "low_cutoff": 240}, "back_to_grid", 30)


class FrameTests(unittest.TestCase):
    def test_read_request(self):
        self.assertEqual(read_request(4501, 21).hex(" "), "05 03 11 95 00 15 90 91")
        with self.assertRaises(ValueError):
            read_request(4561, 10)

    def test_write_frames_from_docs(self):
        self.assertEqual(write_request(5018, 1).hex(" "), "05 06 13 9a 00 01 6d 25")
        self.assertEqual(write_request(5017, 0).hex(" "), "05 06 13 99 00 00 5c e5")
        self.assertEqual(write_request(5017, 2).hex(" "), "05 06 13 99 00 02 dd 24")

    def test_echo_and_refusal(self):
        req = write_request(5018, 1)
        check_write_echo(req, req)
        with self.assertRaises(WriteRefused):
            check_write_echo(req, bytes.fromhex("05 86 82 83 c0"))
        with self.assertRaises(ValueError):
            check_write_echo(req, write_request(5018, 2))

    def test_write_register_is_read_plus_481(self):
        for c in CONTROLS.values():
            if c.read_register:
                self.assertEqual(c.write_register, c.read_register + 481, c.key)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.v = decode_block(dump_words())

    def test_ranges_and_steps(self):
        self.assertEqual(CONTROLS["total_charge_current"].encode("70"), 70)
        self.assertEqual(CONTROLS["back_to_grid"].encode("24.5"), 245)
        self.assertEqual(CONTROLS["output_voltage_setting"].encode("230 V"), 230)
        self.assertEqual(CONTROLS["battery_type"].encode("LIL"), 6)
        self.assertEqual(CONTROLS["alarm"].encode("ON"), 1)
        for key, bad in [("total_charge_current", "75"), ("total_charge_current", "130"),
                         ("grid_charge_current", "5"), ("back_to_grid", "24.3"), ("low_cutoff", "26"),
                         ("battery_type", "XYZ"), ("alarm", "1")]:
            with self.assertRaises(ValueError, msg=f"{key}={bad}"):
                CONTROLS[key].encode(bad)

    def test_cross_rules(self):
        validate_rules(self.v, "total_charge_current", "70")
        with self.assertRaises(ValueError):
            validate_rules(self.v, "grid_charge_current", "50")  # grid > total 40
        with self.assertRaises(ValueError):
            validate_rules(self.v, "low_cutoff", "24.5")      # cutoff must be < back to grid 24.5
        with self.assertRaises(ValueError):
            validate_rules(self.v, "back_to_grid", "21.5")    # must stay > cutoff 24.0
        with self.assertRaises(ValueError):
            validate_rules(self.v, "back_to_battery", "24.5") # must stay > back to grid 24.5
        with self.assertRaises(ValueError):
            validate_rules(self.v, "float_voltage", "28.5")   # float <= bulk 28.4
        validate_rules(self.v, "float_voltage", "28.4")


class LockTests(unittest.TestCase):
    """The bridge must refuse to write without the HA locks and never touch BLE."""

    def make_bridge(self):
        os.environ.setdefault("RWB1_DTU_ID", "000000000000")
        os.environ.setdefault("RWB1_BLE_ADDRESS", "00:00:00:00:00:00")
        import bridge
        args = type("A", (), {"once": True, "interval": 30})()
        b = bridge.Bridge(args)
        b.published = []
        b.publish = lambda topic, payload, retain=True: b.published.append((topic, payload))
        return b

    class NoBLE:
        async def read_block(self):
            raise AssertionError("must not read/write without locks")

        async def query(self, _):
            raise AssertionError("must not write without locks")

    def test_write_blocked_without_locks(self):
        b = self.make_bridge()
        asyncio.run(b._execute(self.NoBLE(), "output_source", "USB"))
        self.assertIn("blocked", b.published[-1][1])

    def test_group_c_needs_both_locks(self):
        b = self.make_bridge()
        b.locks = {"edit": True, "critical": False}
        asyncio.run(b._execute(self.NoBLE(), "battery_type", "LIL"))
        self.assertIn("Critical settings", b.published[-1][1])

    def test_group_c_select_only_prepares(self):
        b = self.make_bridge()
        b.values = {"battery_type": "LIL"}
        b.handle_message(f"{b.base}/set/battery_type", "LIB")
        self.assertTrue(b.commands.empty())
        self.assertIn("battery_type", b.pending)
        b.handle_message(f"{b.base}/apply/battery_type", "PRESS")
        self.assertEqual(b.commands.get_nowait(), ("battery_type", "LIB"))

    def test_discovery_has_controls_and_removes_old_sensors(self):
        b = self.make_bridge()
        b.publish_discovery()
        topics = [t for t, _ in b.published]
        self.assertTrue(any("/select/" in t and t.endswith("/output_source/config") for t in topics))
        self.assertTrue(any("/text/" in t and t.endswith("/bulk_voltage/config") for t in topics))
        self.assertTrue(any("/number/" in t and t.endswith("/total_charge_current/config") for t in topics))
        self.assertTrue(any("/switch/" in t and t.endswith("/alarm/config") for t in topics))
        self.assertTrue(any("/button/" in t and t.endswith("/battery_type_apply/config") for t in topics))
        removed = [t for t, p in b.published if p == ""]
        self.assertTrue(any(t.endswith("/charger_priority_code/config") for t in removed))
        configs = [p for _, p in b.published if isinstance(p, dict)]
        self.assertTrue(all(c["unique_id"].startswith("rwb1_ble_") for c in configs))


if __name__ == "__main__":
    unittest.main()
