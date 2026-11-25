r"""Inspect the OpenPIE-0.6 checkpoint without loading all weights into memory.

Examples:
    python inspect_checkpoint.py
    python inspect_checkpoint.py --model-dir C:\\models\\openpie-0.6
    python inspect_checkpoint.py --repo-id exla-ai/openpie-0.6
    python inspect_checkpoint.py --implementation-root C:\path\to\openpie-code

The Hugging Face repository contains the checkpoint files, not the complete
model implementation. This script reports that distinction explicitly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from checkpoint_contract import CheckpointContract

DEFAULT_REPO_ID = "exla-ai/openpie-0.6"
EXPECTED_FILES = ("config.json", "policy.safetensors", "value_fn.safetensors")


def load_config(model_dir: Path) -> dict[str, Any]:
    config_path = model_dir / "config.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing checkpoint config: {config_path}")
    with config_path.open(encoding="utf-8") as file:
        config = json.load(file)
    if not isinstance(config, dict):
        raise ValueError(f"Expected a JSON object in {config_path}")
    return config


def download_snapshot(repo_id: str, cache_dir: Path | None) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required when --model-dir is not supplied. "
            "Install it with: pip install huggingface_hub"
        ) from exc

    snapshot = snapshot_download(
        repo_id=repo_id,
        allow_patterns=list(EXPECTED_FILES),
        cache_dir=str(cache_dir) if cache_dir else None,
    )
    return Path(snapshot)


def inspect_safetensors(path: Path) -> tuple[int, int, list[tuple[str, tuple[int, ...]]]]:
    try:
        from safetensors import safe_open
    except ImportError as exc:
        raise RuntimeError(
            "safetensors is required to inspect model weights. "
            "Install it with: pip install safetensors"
        ) from exc

    tensor_count = 0
    parameter_count = 0
    selected_shapes: list[tuple[str, tuple[int, ...]]] = []
    with safe_open(str(path), framework="pt", device="cpu") as file:
        for key in file.keys():
            shape = tuple(file.get_slice(key).get_shape())
            tensor_count += 1
            parameter_count += _product(shape)
            if _is_interesting_key(key):
                selected_shapes.append((key, shape))
    return tensor_count, parameter_count, selected_shapes


def _product(values: tuple[int, ...]) -> int:
    result = 1
    for value in values:
        result *= value
    return result


def _is_interesting_key(key: str) -> bool:
    return any(
        marker in key
        for marker in (
            "action_in_proj",
            "action_out_proj",
            "time_mlp",
            "state",
            "gripper",
        )
    )


def scan_implementation(root: Path) -> list[Path]:
    markers = ("class OpenPIE", "action_in_proj", "value_function", "PaliGemma")
    matches: list[Path] = []
    for path in root.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(marker in text for marker in markers):
            matches.append(path)
    return matches


def print_report(model_dir: Path, config: dict[str, Any], implementation_root: Path | None) -> None:
    print(f"Checkpoint directory: {model_dir}")
    print("\nRequired files:")
    for filename in EXPECTED_FILES:
        path = model_dir / filename
        status = "present" if path.is_file() else "missing"
        size = f" ({path.stat().st_size / 1e9:.2f} GB)" if path.is_file() else ""
        print(f"  {filename}: {status}{size}")

    print("\nConfiguration:")
    contract = CheckpointContract.from_config(config)
    print("  contract: validated OpenPIE-0.6 dimensions")
    for key in (
        "base_vlm_variant",
        "action_expert_variant",
        "value_function_variant",
        "repo_id",
        "action_dim",
        "action_horizon",
        "state_dim",
        "dtype",
        "max_token_len",
    ):
        if key in config:
            print(f"  {key}: {config[key]}")

    for filename in ("policy.safetensors", "value_fn.safetensors"):
        path = model_dir / filename
        if not path.is_file():
            continue
        tensors, parameters, shapes = inspect_safetensors(path)
        print(f"\n{filename}:")
        print(f"  tensors: {tensors}")
        print(f"  parameters: {parameters:,} ({parameters / 1e9:.2f}B)")
        if shapes:
            print("  selected tensor shapes:")
            for key, shape in shapes:
                print(f"    {key}: {shape}")

    print("\nImplementation status:")
    if implementation_root is None:
        print("  No implementation root supplied.")
        print("  The Hugging Face snapshot provides weights and config, not model source.")
    else:
        matches = scan_implementation(implementation_root)
        if matches:
            print(f"  Candidate source files under {implementation_root}:")
            for path in matches:
                print(f"    {path}")
        else:
            print(f"  No candidate Python implementation found under {implementation_root}.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--model-dir", type=Path, help="Local checkpoint directory.")
    source.add_argument("--repo-id", default=DEFAULT_REPO_ID, help="Hugging Face model repository.")
    parser.add_argument("--cache-dir", type=Path, help="Hugging Face cache directory.")
    parser.add_argument(
        "--implementation-root",
        type=Path,
        help="Optional source tree to scan for a complete model implementation.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        model_dir = args.model_dir or download_snapshot(args.repo_id, args.cache_dir)
        config = load_config(model_dir)
        print_report(model_dir, config, args.implementation_root)
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
