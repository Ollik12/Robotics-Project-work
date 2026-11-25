"""Export OpenPIE safetensors names and shapes without loading tensor data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def dump_keys(checkpoint: Path, output: Path) -> int:
    try:
        from safetensors import safe_open
    except ImportError as exc:
        raise RuntimeError(
            "safetensors is required. Install it with: pip install safetensors"
        ) from exc

    if not checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")

    tensors: list[dict[str, Any]] = []
    with safe_open(str(checkpoint), framework="pt", device="cpu") as file:
        for key in file.keys():
            tensor = file.get_slice(key)
            tensors.append({"name": key, "shape": list(tensor.get_shape())})

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "checkpoint": str(checkpoint),
                "tensor_count": len(tensors),
                "tensors": tensors,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(tensors)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="policy.safetensors or value_fn.safetensors")
    parser.add_argument("output", type=Path, help="JSON file to create")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        count = dump_keys(args.checkpoint, args.output)
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {count} tensor entries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
