"""Tests for Jackery protocol helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPO_ROOT / "custom_components" / "jackery" / "protocol.py"


def load_protocol_module():
    """Load the protocol helper without importing Home Assistant modules."""
    spec = importlib.util.spec_from_file_location("jackery_protocol", PROTOCOL_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(spec.name)
    sys.modules[spec.name] = module
    try:
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_module is None:
            sys.modules.pop(spec.name, None)
        else:
            sys.modules[spec.name] = previous_module


protocol = load_protocol_module()


class ProtocolTests(unittest.TestCase):
    """Validate control metadata and capability detection."""

    def test_load_protocol_module_cleans_up_temporary_sys_modules_entry(self) -> None:
        """Loading the helper should not leak its temporary import alias."""
        sys.modules.pop("jackery_protocol", None)

        module = load_protocol_module()

        self.assertEqual(module.__name__, "jackery_protocol")
        self.assertNotIn("jackery_protocol", sys.modules)

    def test_load_protocol_module_restores_previous_sys_modules_entry(self) -> None:
        """Existing module entries should be restored after loading."""
        existing_module = types.ModuleType("jackery_protocol")
        sys.modules["jackery_protocol"] = existing_module
        self.addCleanup(sys.modules.pop, "jackery_protocol", None)

        module = load_protocol_module()

        self.assertEqual(module.__name__, "jackery_protocol")
        self.assertIs(sys.modules["jackery_protocol"], existing_module)

    def test_control_specs_match_known_jackery_write_slugs(self) -> None:
        """Confirmed writable controls should preserve the correct API slug."""
        expected = {
            "oac": "ac",
            "odc": "dc",
            "odcu": "usb",
            "odcc": "car",
            "sfc": "sfc",
            "lm": "light",
            "cs": "charge-speed",
            "lps": "battery-protection",
            "ast": "auto-shutdown",
            "pm": "energy-saving",
            "sltb": "screen-timeout",
        }

        actual = {
            key: protocol.control_spec(key).slug
            for key in expected
        }
        self.assertEqual(actual, expected)

    def test_combined_dc_output_suppresses_split_outputs(self) -> None:
        """Devices with only combined DC should not expose USB/car controls."""
        properties = {"odc": 1}

        self.assertEqual(
            protocol.supported_keys(properties, ("odc", "odcu", "odcc")),
            ("odc",),
        )
        self.assertTrue(protocol.is_supported_property(properties, "odc"))
        self.assertFalse(protocol.is_supported_property(properties, "odcu"))
        self.assertFalse(protocol.is_supported_property(properties, "odcc"))

    def test_split_dc_outputs_suppress_combined_toggle(self) -> None:
        """Devices with dedicated USB/car controls should hide combined DC."""
        properties = {"odc": 1, "odcu": 0, "odcc": 1}

        self.assertEqual(
            protocol.supported_keys(properties, ("odc", "odcu", "odcc")),
            ("odcu", "odcc"),
        )
        self.assertFalse(protocol.is_supported_property(properties, "odc"))

    def test_screen_timeout_accepts_alias_read_key(self) -> None:
        """Some code paths refer to screen timeout as slt rather than sltb."""
        self.assertTrue(protocol.is_supported_property({"sltb": 30}, "sltb"))
        self.assertTrue(protocol.is_supported_property({"slt": 30}, "sltb"))

    def test_charging_plan_support_is_split_by_dp(self) -> None:
        """Charging-plan entities should be gated by the DP they actually use."""
        self.assertTrue(protocol.has_charging_plan_switch_support({"107": 1}))
        self.assertFalse(
            protocol.has_charging_plan_switch_support(
                {"108": "22:00-06:00,1111111"}
            )
        )
        self.assertFalse(protocol.has_charging_plan_data_support({"107": 1}))
        self.assertTrue(
            protocol.has_charging_plan_data_support(
                {"108": "22:00-06:00,1111111"}
            )
        )
        self.assertTrue(
            protocol.has_charging_plan_switch_support(
                {"107": 1, "108": "22:00-06:00,1111111"}
            )
        )
        self.assertTrue(
            protocol.has_charging_plan_data_support(
                {"107": 1, "108": "22:00-06:00,1111111"}
            )
        )

    def test_known_charging_plan_models_support_entities_without_dps(self) -> None:
        """Known compatible models should surface charging-plan entities without DP hints."""
        device_info = {"devName": "Explorer 5000 Plus"}

        self.assertTrue(protocol.has_known_charging_plan_model(device_info))
        self.assertTrue(protocol.has_charging_plan_switch_support({}, device_info))
        self.assertTrue(protocol.has_charging_plan_data_support({}, device_info))
        self.assertFalse(
            protocol.has_known_charging_plan_model({"devName": "Explorer 2000 Plus"})
        )

    def test_parse_and_compose_charging_plan(self) -> None:
        """Charging-plan helpers should preserve valid payloads."""
        self.assertEqual(
            protocol.parse_charging_plan("22:00-06:00,0111110"),
            ("22:00-06:00", "0111110"),
        )
        self.assertEqual(
            protocol.compose_charging_plan("22:00-06:00", "0111110"),
            "22:00-06:00,0111110",
        )
        self.assertEqual(
            protocol.charging_plan_repeat_option("0111110"),
            "Weekdays",
        )
        self.assertEqual(
            protocol.charging_plan_repeat_mask("Weekends"),
            "1000001",
        )

    def test_parse_charging_plan_rejects_malformed_values(self) -> None:
        """Malformed charging-plan payloads should be rejected."""
        self.assertIsNone(protocol.parse_charging_plan(None))
        self.assertIsNone(protocol.parse_charging_plan("22:00-06:00"))
        self.assertIsNone(protocol.parse_charging_plan("22:00-06:00,010101"))
        self.assertIsNone(protocol.parse_charging_plan("25:00-06:00,1111111"))

        with self.assertRaises(ValueError):
            protocol.compose_charging_plan("25:00-06:00", "1111111")
        with self.assertRaises(ValueError):
            protocol.compose_charging_plan("22:00-06:00", "invalid")

    def test_new_controls_only_show_when_reported(self) -> None:
        """Recovered controls should be filtered directly from reported properties."""
        properties = {
            "oac": 1,
            "sfc": 0,
            "lm": 2,
            "cs": 1,
            "lps": 0,
            "ast": 30,
            "pm": 20,
            "sltb": 15,
        }

        self.assertEqual(
            protocol.supported_keys(
                properties,
                ("oac", "sfc", "lm", "cs", "lps", "ast", "pm", "sltb"),
            ),
            ("oac", "sfc", "lm", "cs", "lps", "ast", "pm", "sltb"),
        )
        self.assertFalse(protocol.is_supported_property(properties, "charging_plan"))

    def test_portable_control_specs_have_action_ids(self) -> None:
        """All portable writable properties must carry a non-None action_id."""
        portable_keys = ("oac", "odc", "odcu", "odcc", "sfc", "lm", "cs", "lps", "ast", "pm", "sltb")
        for key in portable_keys:
            spec = protocol.control_spec(key)
            self.assertIsNotNone(spec.action_id, f"{key} is missing action_id")

    def test_transfer_switch_control_specs_have_no_action_id(self) -> None:
        """Transfer Switch properties must NOT carry a portable action_id."""
        ts_keys = ("ddt", "en", "ups", "pss", "rc")
        for key in ts_keys:
            spec = protocol.control_spec(key)
            self.assertIsNone(spec.action_id, f"{key} should not have a portable action_id")

    def test_sltb_prop_key_is_slt(self) -> None:
        """Screen timeout writes 'slt' to the MQTT body, not 'sltb'."""
        spec = protocol.control_spec("sltb")
        self.assertEqual(spec.prop_key, "slt")

    def test_prop_key_defaults_to_key(self) -> None:
        """Controls without a write_key should use the property key verbatim."""
        spec = protocol.control_spec("oac")
        self.assertEqual(spec.prop_key, "oac")

    def test_control_specs_by_slug_reverse_lookup(self) -> None:
        """Slug-indexed lookup must resolve back to the correct property key."""
        self.assertEqual(protocol.CONTROL_SPECS_BY_SLUG["ac"].key, "oac")
        self.assertEqual(protocol.CONTROL_SPECS_BY_SLUG["screen-timeout"].key, "sltb")
        self.assertEqual(protocol.CONTROL_SPECS_BY_SLUG["screen-timeout"].prop_key, "slt")

    def test_is_transfer_switch_device_by_model_code(self) -> None:
        """modelCode 2001 must always classify as Transfer Switch."""
        self.assertTrue(protocol.is_transfer_switch_device({"modelCode": 2001}))
        self.assertFalse(protocol.is_transfer_switch_device({"modelCode": 13}))
        self.assertFalse(protocol.is_transfer_switch_device({}))

    def test_is_transfer_switch_device_by_properties(self) -> None:
        """Unknown modelCode but Transfer Switch property markers → classified as TS."""
        # Flattened coordinator data (post-flatten)
        self.assertTrue(protocol.is_transfer_switch_device({"modelCode": 9999}, {"ac1_rb": 80}))
        self.assertTrue(protocol.is_transfer_switch_device({}, {"fz_gs": 0}))
        # Raw HTTP properties (pre-flatten)
        self.assertTrue(protocol.is_transfer_switch_device({}, {"ac1": {"rb": 80}}))
        self.assertTrue(protocol.is_transfer_switch_device({}, {"cds": [], "fz": {}}))
        # Portable properties should not trigger TS classification
        self.assertFalse(protocol.is_transfer_switch_device({}, {"rb": 90, "oac": 1}))

    def test_is_transfer_switch_device_model_code_takes_priority(self) -> None:
        """modelCode 2001 must win even without marker properties."""
        self.assertTrue(protocol.is_transfer_switch_device({"modelCode": 2001}, {}))


if __name__ == "__main__":
    unittest.main()
