# OpenPIE-0.6 workspace

This folder contains the repository-side tooling for evaluating OpenPIE-0.6
with the single-arm Franka/CRISP setup.

## Contents

- `inspect_checkpoint.py`: inspect `config.json` and safetensors headers without
  loading the full checkpoint into RAM.
- `checkpoint_contract.py`: validate the published dimensions before model
  reconstruction.
- `dump_checkpoint_keys.py`: export every tensor name and shape to JSON without
  loading tensor data.
- `openpie_14d_to_7d.py`: select one 7D arm slot from a 14D action or action
  chunk.
- `tests/test_action_adapter.py`: focused tests for the pure action adapter.
- `model_config.py`: OpenPI PyTorch configuration matching the OpenPIE policy.
- `load_policy.py`: construct the public OpenPI PyTorch model and strictly load
  the OpenPIE policy checkpoint.
- `tpu_fsdp_inference.py`: launch one XLA FSDP process per TPU core and load the
  policy with bfloat16 parameters.

The checkpoint itself is intentionally not committed to this repository. The
Hugging Face files are approximately 12 GB for the policy and 2.5 GB for the
value function.

## Download and inspect

Install the inspection dependencies:

```bash
pip install huggingface_hub safetensors
```

Download and inspect the snapshot:

```bash
python openpie-0.6/inspect_checkpoint.py
```

Inspect an existing local download:

```bash
python openpie-0.6/inspect_checkpoint.py \
  --model-dir /path/to/openpie-0.6
```

Scan a separate source tree for a possible complete implementation:

```bash
python openpie-0.6/inspect_checkpoint.py \
  --model-dir /path/to/openpie-0.6 \
  --implementation-root /path/to/openpie-source
```

The Hugging Face repository currently provides the weights and configuration,
but not the complete model source or inference server.

Export checkpoint keys after downloading the files:

```bash
python openpie-0.6/dump_checkpoint_keys.py \
  /path/to/openpie-0.6/policy.safetensors \
  openpie-0.6/policy_keys.json
```

The generated JSON is local reconstruction evidence and should not be
committed with model artifacts.

## Validate policy loading in Kaggle

The loader uses the public OpenPI source tree and the local OpenPIE policy
checkpoint. From the Kaggle environment:

```bash
python openpie-0.6/load_policy.py \
  --checkpoint /kaggle/working/openpie-0.6/policy.safetensors \
  --openpi-source /kaggle/working/openpi-source \
  --device cpu
```

The default is strict loading. It must report no missing or unexpected keys.
Use `--allow-partial` only for diagnosis; a partially initialized policy must
not be used for inference.

The public OpenPI implementation requires its normal dependencies, including
PyTorch, Transformers, and the repository's transformers replacement. This
loader validates checkpoint compatibility; it does not yet connect the policy
to ROS or CRISP.

## Load on a TPU v5e-8

The CUDA loader must not be used on a T4 for this checkpoint: it constructs an
unsharded 5.9B-parameter model and can exhaust device memory. A TPU v5e-8 has
eight TPU devices, so use the XLA FSDP launcher instead:

```bash
pip install torch_xla[tpu] safetensors transformers==4.53.2
python openpie-0.6/tpu_fsdp_inference.py \
  --checkpoint /kaggle/working/openpie-0.6/policy.safetensors \
  --openpi-source /kaggle/working/openpi-source
```

The launcher creates one process per TPU device, wraps transformer submodules
with `XlaFullyShardedDataParallel`, uses bfloat16 compute, and performs strict
loading. The checkpoint is read into host memory before FSDP loads and shards
it; this avoids a single-device HBM allocation but still requires sufficient
host RAM. The PaliGemma tied-embedding compatibility fix from
`load_policy.py` is preserved.

This validates distributed model construction and checkpoint loading only. It
does not yet define the real image/token/state observation tensors or prove
that OpenPIE's 14D actions have CRISP's Cartesian 7D semantics. Do not send
the output to the robot until those contracts are verified.

## 14D to 7D conversion

For an action shaped `(horizon, 14)`, select one arm slot:

```bash
python openpie-0.6/openpie_14d_to_7d.py \
  openpie_actions.npy \
  franka_actions.npy \
  --arm left
```

This only selects the slot. It does not convert joint-space actions into
Cartesian CRISP actions. Confirm the OpenPIE action semantics before sending
the result to a controller.

Validate a model-shaped action chunk before selecting an arm:

```python
import numpy as np

from openpie_14d_to_7d import select_arm_action, validate_action_chunk

actions = np.load("openpie_actions.npy")
validated = validate_action_chunk(actions, expected_horizon=50)
franka_actions = select_arm_action(validated, arm="left")
assert franka_actions.shape == (50, 7)
```

The validation checks rank, 14D width, optional 50-step horizon, numeric
dtype, and finite values. It does not establish whether the seven values are
joint-space or Cartesian commands; that requires matching the OpenPIE
preprocessing and training-data action specification.
