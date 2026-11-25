"""Verified and expected metadata for the OpenPIE-0.6 checkpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EXPECTED_REPO_ID = "exla-ai/openpie-0.6"
EXPECTED_ACTION_DIM = 14
EXPECTED_STATE_DIM = 14
EXPECTED_ACTION_HORIZON = 50


@dataclass(frozen=True)
class CheckpointContract:
    """Validated shape metadata read from OpenPIE-0.6 config.json."""

    action_dim: int
    state_dim: int
    action_horizon: int
    dtype: str
    repo_id: str | None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "CheckpointContract":
        required = ("action_dim", "state_dim", "action_horizon", "dtype")
        missing = [key for key in required if key not in config]
        if missing:
            raise ValueError(f"Missing required config fields: {', '.join(missing)}")

        contract = cls(
            action_dim=_positive_int(config["action_dim"], "action_dim"),
            state_dim=_positive_int(config["state_dim"], "state_dim"),
            action_horizon=_positive_int(config["action_horizon"], "action_horizon"),
            dtype=_non_empty_string(config["dtype"], "dtype"),
            repo_id=config.get("repo_id"),
        )
        contract.validate_openpie_defaults()
        return contract

    def validate_openpie_defaults(self) -> None:
        mismatches = []
        if self.action_dim != EXPECTED_ACTION_DIM:
            mismatches.append(f"action_dim={self.action_dim}")
        if self.state_dim != EXPECTED_STATE_DIM:
            mismatches.append(f"state_dim={self.state_dim}")
        if self.action_horizon != EXPECTED_ACTION_HORIZON:
            mismatches.append(f"action_horizon={self.action_horizon}")
        if mismatches:
            raise ValueError(
                "Config does not match the published OpenPIE-0.6 contract: "
                + ", ".join(mismatches)
            )


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer; received {value!r}.")
    return value


def _non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string; received {value!r}.")
    return value
