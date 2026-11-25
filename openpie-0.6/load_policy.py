"""Construct the public OpenPI PyTorch model and validate OpenPIE-0.6 weights.

The OpenPI source tree must be supplied separately because the Hugging Face
OpenPIE repository contains weights and configuration, not Python modules.
This script intentionally fails on missing or unexpected keys by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_config import openpie_policy_config
def make_model_config() -> SimpleNamespace:
    """Create the OpenPI PyTorch config matching the OpenPIE checkpoint."""
    return openpie_policy_config()


def import_openpi_model(source_root: Path):
    source_path = source_root / "src"
    if not source_path.is_dir():
        raise FileNotFoundError(f"OpenPI source src directory not found: {source_path}")
    sys.path.insert(0, str(source_path))
    try:
        from openpi.models_pytorch.pi0_pytorch import PI0Pytorch
    except ImportError as exc:
        raise RuntimeError(
            "Could not import OpenPI PI0Pytorch. Install the OpenPI dependencies "
            "and its required transformers replacement first."
        ) from exc
    return PI0Pytorch


def load_policy(
    checkpoint: Path,
    source_root: Path,
    *,
    device: str = "cpu",
    strict: bool = True,
):
    """Construct and load the policy, returning the model and load report."""
    try:
        import torch
        from safetensors.torch import load_file
    except ImportError as exc:
        raise RuntimeError(
            "Install torch and safetensors before loading the policy."
        ) from exc

    if not checkpoint.is_file():
        raise FileNotFoundError(f"Policy checkpoint not found: {checkpoint}")

    policy_class = import_openpi_model(source_root)
    config = make_model_config()
    model = policy_class(config)
    state_dict = load_file(str(checkpoint), device=device)
    embedding_key = (
        "paligemma_with_expert.paligemma.model.language_model.embed_tokens.weight"
    )
    tied_output_key = "paligemma_with_expert.paligemma.lm_head.weight"
    if embedding_key not in state_dict and tied_output_key in state_dict:
        state_dict[embedding_key] = state_dict[tied_output_key]
    incompatible = model.load_state_dict(state_dict, strict=strict)
    model.to(device)
    model.eval()
    report = {
        "device": device,
        "strict": strict,
        "missing_keys": list(incompatible.missing_keys),
        "unexpected_keys": list(incompatible.unexpected_keys),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "torch_dtype": str(next(model.parameters()).dtype),
    }
    return model, report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--openpi-source", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Report missing/unexpected keys instead of failing strict loading.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        _, report = load_policy(
            args.checkpoint,
            args.openpi_source,
            device=args.device,
            strict=not args.allow_partial,
        )
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
