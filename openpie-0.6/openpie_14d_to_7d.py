"""Adapt an OpenPIE-0.6 action chunk for a single-arm consumer.

OpenPIE-0.6 publishes a 14-dimensional action for two 7-dimensional arm
slots. This adapter selects one slot and does not infer a Cartesian action
from it. The selected values must already have the semantics expected by the
downstream controller.
"""

from __future__ import annotations

import argparse
from enum import IntEnum
from pathlib import Path

import numpy as np


MODEL_ACTION_DIM = 14
ARM_ACTION_DIM = 7


class ArmSlot(IntEnum):
    """The two 7D slots in the OpenPIE action."""

    LEFT = 0
    RIGHT = 1


def select_arm_action(
    actions: np.ndarray,
    arm: ArmSlot | int | str = ArmSlot.LEFT,
    *,
    expected_action_dim: int = MODEL_ACTION_DIM,
) -> np.ndarray:
    """Select one arm from an OpenPIE action or action chunk."""
    array = np.asarray(actions)
    if array.ndim not in (1, 2) or array.shape[-1] != expected_action_dim:
        raise ValueError(
            "Expected an action with shape (14,) or (horizon, 14); "
            f"received {array.shape}."
        )

    slot = _parse_arm_slot(arm)
    start = int(slot) * ARM_ACTION_DIM
    end = start + ARM_ACTION_DIM
    return np.array(array[..., start:end], copy=True)


def validate_action_chunk(
    actions: np.ndarray,
    *,
    expected_horizon: int | None = None,
    expected_action_dim: int = MODEL_ACTION_DIM,
) -> np.ndarray:
    """Validate an OpenPIE action or chunk without changing its values."""
    array = np.asarray(actions)
    if array.ndim not in (1, 2) or array.shape[-1] != expected_action_dim:
        raise ValueError(
            "Expected an action with shape (14,) or (horizon, 14); "
            f"received {array.shape}."
        )
    if expected_horizon is not None and array.ndim == 2 and array.shape[0] != expected_horizon:
        raise ValueError(
            f"Expected an action horizon of {expected_horizon}; "
            f"received {array.shape[0]}."
        )
    if not np.issubdtype(array.dtype, np.number):
        raise TypeError(f"Expected numeric actions; received dtype {array.dtype}.")
    if not np.isfinite(array).all():
        raise ValueError("Actions must contain only finite values.")
    return array


def _parse_arm_slot(arm: ArmSlot | int | str) -> ArmSlot:
    if isinstance(arm, ArmSlot):
        return arm
    if isinstance(arm, int):
        try:
            return ArmSlot(arm)
        except ValueError as exc:
            raise ValueError("Arm slot must be 0 (left) or 1 (right).") from exc

    normalized = arm.strip().lower()
    if normalized == "left":
        return ArmSlot.LEFT
    if normalized == "right":
        return ArmSlot.RIGHT
    raise ValueError("Arm must be 'left', 'right', 0, or 1.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select one 7D arm action from an OpenPIE 14D action chunk."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input .npy file containing shape (14,) or (horizon, 14).",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Output .npy file containing shape (7,) or (horizon, 7).",
    )
    parser.add_argument(
        "--arm",
        choices=("left", "right"),
        default="left",
        help="OpenPIE arm slot to execute.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    actions = np.load(args.input)
    selected = select_arm_action(actions, args.arm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, selected)
    print(f"Saved {selected.shape} action array to {args.output}")


if __name__ == "__main__":
    main()
