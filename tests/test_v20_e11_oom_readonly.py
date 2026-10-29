#!/usr/bin/env python3
"""Host-only fail-closed regression for the read-only E11 heap probe."""
import importlib.util
import pathlib
import types
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "diagnose-v20-e11-oom-readonly.py"
spec = importlib.util.spec_from_file_location("e11_oom_readonly", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

VALID = (
    "Free heap size: 103024\r\n"
    "Total heap size: 189200\r\n"
    "Minimum heap size: 62800\r\n"
    "Maximum heap block: 34600\r\n"
    "Pool free: 1024\r\n"
    "Maximum pool block: 512\r\n"
)


def fake_port(device, description, manufacturer=None, product=None, vid=None, pid=None):
    return types.SimpleNamespace(
        device=device, description=description,
        manufacturer=manufacturer, product=product, vid=vid, pid=pid
    )


class E11MemoryReadOnly(unittest.TestCase):
    def test_complete_snapshot(self):
        self.assertEqual(module.parse_free(VALID)["Maximum heap block"], 34600)
        self.assertEqual(module.parse_free(VALID)["Free heap size"], 103024)

    def test_incomplete_does_not_infer_memory(self):
        self.assertEqual(module.parse_free(VALID.split("Pool free:")[0]), {})
        self.assertEqual(module.parse_free("Error: Out of Memory"), {})
        self.assertEqual(module.parse_free(""), {})

    def test_escaped_ansi_echo_ignored(self):
        self.assertEqual(module.parse_free("Flipper CLI> free\r\n" + VALID + "Flipper CLI>"),
                         module.parse_free(VALID))

    def test_usb_flipper_identification(self):
        ports = [fake_port("COM2", "Bluetooth"), fake_port("COM7", "Flipper Zero CDC")]
        self.assertEqual(module.choose_port(ports, None), "COM7")
        self.assertEqual(module.choose_port(ports, "COM7"), "COM7")

    def test_usb_vid_fallback(self):
        ports = [fake_port("COM7", "USB Serial", vid=0x0483, pid=0x5740)]
        self.assertEqual(module.choose_port(ports, None), "COM7")

    def test_no_guess_ambiguous_or_missing(self):
        ports = [fake_port("COM7", "Flipper Zero"), fake_port("COM8", "Flipper Zero")]
        with self.assertRaises(ValueError):
            module.choose_port(ports, None)
        with self.assertRaises(ValueError):
            module.choose_port(ports, "COM9")
        with self.assertRaises(ValueError):
            module.choose_port([], None)

    def test_no_device_write_or_destructive_commands(self):
        src = PATH.read_text(encoding="utf-8")
        self.assertIn('cli.write(b"\\rfree\\r")', src)
        self.assertEqual(src.count("cli.write("), 1)
        self.assertNotIn("storage write", src)
        self.assertNotIn("loader_start(", src)
        self.assertNotIn("firmware flash", src.lower().replace("no ", ""))


if __name__ == "__main__":
    unittest.main()
