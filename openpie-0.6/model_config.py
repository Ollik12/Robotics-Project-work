"""OpenPIE-0.6 policy configuration shared by reconstruction tools."""

from __future__ import annotations

from types import SimpleNamespace


def openpie_policy_config() -> SimpleNamespace:
    """Return fields consumed by OpenPI's PyTorch PI0Pytorch class."""
    return SimpleNamespace(
        pi05=True,
        action_dim=14,
        action_horizon=50,
        paligemma_variant="gemma_2b",
        action_expert_variant="gemma_2b",
        dtype="bfloat16",
        pytorch_compile_mode=None,
    )
