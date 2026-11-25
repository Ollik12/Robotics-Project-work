"""Tests for the pure OpenPIE action-slot adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "openpie_14d_to_7d",
    ROOT / "openpie_14d_to_7d.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load the action adapter.")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ActionAdapterTests(unittest.TestCase):
    def test_selects_left_slot_from_chunk(self) -> None:
        actions = np.arange(70, dtype=np.float32).reshape(5, 14)
        result = MODULE.select_arm_action(actions, "left")
        np.testing.assert_array_equal(result, actions[:, :7])

    def test_selects_right_slot_from_single_action(self) -> None:
        action = np.arange(14, dtype=np.float32)
        result = MODULE.select_arm_action(action, "right")
        np.testing.assert_array_equal(result, action[7:])

    def test_rejects_wrong_rank(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.select_arm_action(np.zeros((1, 2, 14)), "left")

    def test_rejects_wrong_dimension(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.select_arm_action(np.zeros((5, 7)), "left")

    def test_rejects_invalid_arm(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.select_arm_action(np.zeros(14), "middle")

    def test_validates_expected_horizon_and_finite_values(self) -> None:
        actions = np.zeros((50, 14), dtype=np.float32)
        result = MODULE.validate_action_chunk(actions, expected_horizon=50)
        np.testing.assert_array_equal(result, actions)

    def test_rejects_wrong_horizon(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.validate_action_chunk(np.zeros((10, 14)), expected_horizon=50)

    def test_rejects_non_finite_values(self) -> None:
        actions = np.zeros((50, 14), dtype=np.float32)
        actions[0, 0] = np.nan
        with self.assertRaises(ValueError):
            MODULE.validate_action_chunk(actions, expected_horizon=50)


if __name__ == "__main__":
    unittest.main()
