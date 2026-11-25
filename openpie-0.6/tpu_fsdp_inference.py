"""Load OpenPIE-0.6 with torch_xla FSDP across a TPU v5e pod slice.

This launcher is intentionally separate from ``load_policy.py``. The latter
loads an unsharded PyTorch model for compatibility checks, while this module
creates one XLA FSDP process per TPU core before loading the checkpoint.
"""

from __future__ import annotations

import argparse
from functools import partial
from pathlib import Path
import shutil
import sys


EMBEDDING_KEY = (
    "paligemma_with_expert.paligemma.model.language_model.embed_tokens.weight"
)
TIED_OUTPUT_KEY = "paligemma_with_expert.paligemma.lm_head.weight"


def _install_transformers_replacement(source_root: Path) -> None:
    """Install OpenPI's required Transformers model replacements in-place."""
    import transformers

    replacement_root = (
        source_root
        / "src"
        / "openpi"
        / "models_pytorch"
        / "transformers_replace"
        / "models"
    )
    transformers_root = Path(transformers.__file__).resolve().parent / "models"
    if not replacement_root.is_dir():
        raise FileNotFoundError(
            f"OpenPI Transformers replacement directory not found: {replacement_root}"
        )
    for relative_path in (
        Path("paligemma") / "modeling_paligemma.py",
        Path("gemma") / "configuration_gemma.py",
        Path("gemma") / "modeling_gemma.py",
    ):
        source = replacement_root / relative_path
        destination = transformers_root / relative_path
        if not source.is_file():
            raise FileNotFoundError(f"Replacement file not found: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _build_fsdp_model(source_root: Path):
    """Construct and wrap the OpenPI model for XLA FSDP."""
    import torch
    from torch_xla.distributed.fsdp import XlaFullyShardedDataParallel
    from torch_xla.distributed.fsdp.wrap import size_based_auto_wrap_policy

    source_path = source_root / "src"
    if not source_path.is_dir():
        raise FileNotFoundError(f"OpenPI source src directory not found: {source_path}")
    sys.path.insert(0, str(source_path))

    from openpi.models_pytorch.pi0_pytorch import PI0Pytorch
    from model_config import openpie_policy_config

    model = PI0Pytorch(openpie_policy_config())
    auto_wrap_policy = partial(size_based_auto_wrap_policy, min_num_params=1_000_000)
    return XlaFullyShardedDataParallel(
        model,
        compute_dtype=torch.bfloat16,
        pin_layout_in_collective_ops=True,
        auto_wrap_policy=auto_wrap_policy,
    )


def _load_checkpoint(model, checkpoint: Path, *, strict: bool):
    """Load the full checkpoint on host memory and let FSDP shard parameters."""
    from safetensors.torch import load_file

    if not checkpoint.is_file():
        raise FileNotFoundError(f"Policy checkpoint not found: {checkpoint}")
    state_dict = load_file(str(checkpoint), device="cpu")
    if EMBEDDING_KEY not in state_dict and TIED_OUTPUT_KEY in state_dict:
        state_dict[EMBEDDING_KEY] = state_dict[TIED_OUTPUT_KEY]
    incompatible = model.load_state_dict(state_dict, strict=strict)
    return {
        "missing_keys": list(incompatible.missing_keys),
        "unexpected_keys": list(incompatible.unexpected_keys),
        "checkpoint_tensors": len(state_dict),
    }


def _worker(
    index: int,
    checkpoint: str,
    source_root: str,
    strict: bool,
) -> None:
    import torch_xla.core.xla_model as xm

    device = xm.xla_device()
    source_path = Path(source_root)
    checkpoint_path = Path(checkpoint)
    _install_transformers_replacement(source_path)
    model = _build_fsdp_model(source_path)
    report = _load_checkpoint(model, checkpoint_path, strict=strict)
    model.eval()
    xm.mark_step()

    if index == 0:
        parameter_count = sum(parameter.numel() for parameter in model.parameters())
        print(
            {
                "device": str(device),
                "world_size": xm.xrt_world_size(),
                "parameter_count": parameter_count,
                "torch_dtype": str(next(model.parameters()).dtype),
                **report,
            },
            flush=True,
        )
    del model


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--openpi-source", type=Path, required=True)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Report missing/unexpected keys instead of requiring strict loading.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        import torch_xla

        torch_xla.launch(
            _worker,
            args=(
                str(args.checkpoint),
                str(args.openpi_source),
                not args.allow_partial,
            ),
        )
    except (FileNotFoundError, ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
