# OpenPI Installation

---

## 1. Clone the repository

### On the host

If you don't plan to use LoRA fine-tuning, clone the official OpenPI repository. There, you can run inference or perform full fine-tuning of Pi0 models.

```bash
cd openpi-fr3
git clone --recurse-submodules git@github.com:Physical-Intelligence/openpi.git openpi
```

If you are planning to use LoRA fine-tuning, clone the LoRA fine-tuning fork by `sen-code-lost`:

```bash
cd openpi-fr3
git clone --recurse-submodules git@github.com:sen-code-lost/openpi.git openpi
cd openpi
git switch feat/pytorch-lora
```

---

## 2. Set up OpenPI

Build/rebuild the Docker container after cloning the OpenPI repository. See the [Docker setup instructions](https://github.com/Ollik12/Robotics-Project-work/blob/main/README.md).

### In Docker

Install `uv`:

```bash
cd /ros2_ws/openpi-fr3/openpi
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

Install the OpenPI dependencies inside the `openpi` folder:

```bash
GIT_LFS_SKIP_SMUDGE=1 uv sync
GIT_LFS_SKIP_SMUDGE=1 uv pip install -e .
```

---

# Gazebo Simulation + FR3 + Pi0 Inference

**Note:** Pi0 inference requires more than 12 GB of VRAM. Make sure your GPU has sufficient VRAM before proceeding.


## 1. Install the OpenPI client

Make sure the OpenPI virtual environment is **deactivated** before installing the following packages.

If the OpenPI environment is active, you can deactivate it with:

```bash
deactivate
```

Install `openpi-client` and `typing_extensions`:

```bash
python3 -m pip install --break-system-packages -e /ros2_ws/openpi-fr3/openpi/packages/openpi-client
python3 -m pip install --break-system-packages typing_extensions
```

---

## 2. Activate the OpenPI environment


In Docker terminal:

```bash
cd /ros2_ws/openpi-fr3/openpi
source .venv/bin/activate
```

You should now see `(openpi)` in the shell prompt.

---

## 3. Start the OpenPI policy server

With the OpenPI virtual environment activated:

```bash
uv run scripts/serve_policy.py \
    policy:checkpoint \
    --policy.config=pi05_libero \
    --policy.dir=gs://openpi-assets/checkpoints/pi05_libero
```

This starts the OpenPI policy server using the pretrained `pi05_libero` model. The model is downloaded to `~/.cache/openpi/openpi-assets/checkpoints/` if it is not already available in the cache.

The policy server communicates with the ROS 2 OpenPI client through a WebSocket connection.

---

## 4. Start the FR3 simulation

Open a new Docker terminal and run:

```bash
ros2 launch franka_fm_gazebo sim.launch.py
```

---

## 5. Start the OpenPI ROS 2 node

In another Docker terminal, start the ROS 2 OpenPI inference node:

```bash
ros2 run openpi_ros openpi_inference
```

The node:

1. Receives camera images from Gazebo.

2. Receives the FR3 joint state.

3. Constructs the OpenPI observation.

4. Sends the observation to the OpenPI policy server for inference.

5. Receives the predicted action chunk.

6. TODO: Sends the actions to CRISP to control the robot.

---

# LoRA Fine-tuning

**Note:** LoRA fine-tuning is recommended to be performed on a GPU with at least 16 GB of VRAM.


Make sure you have cloned the LoRA fine-tuning repository from `sen-code-lost`.

## 1. Replace the configuration file

Replace the `config.py` file in `ros2_ws/openpi-fr3/openpi/src/training/config.py` with the provided configuration file from `ros2_ws/openpi-fr3/src/config.py`.

Activate the OpenPI environment:

```bash
cd /ros2_ws/openpi-fr3/openpi
source .venv/bin/activate
```

## 2. Install the required Transformers version

```bash
uv pip install transformers==4.53.2
cp -r ./src/openpi/models_pytorch/transformers_replace/* .venv/lib/python3.11/site-packages/transformers/
```

## 3. Convert the JAX checkpoint to PyTorch

```bash
uv run examples/convert_jax_model_to_pytorch.py \
    --config-name=pi05_libero \
    --checkpoint_dir ~/.cache/openpi/openpi-assets/checkpoints/pi05_libero \
    --output_path ~/.cache/openpi/openpi-assets/checkpoints/pi05_libero_pytorch
```

## 4. Compute the normalization statistics

```bash
uv run scripts/compute_norm_stats.py --config-name=pi05_libero_lora_pytorch
```

## 5. Start LoRA fine-tuning

Before starting the training, you can change the hyperparameters in the `pi05_libero_lora_pytorch` `TrainConfig` in `openpi/src/training/config.py`.

```bash
uv run scripts/train_pytorch.py pi05_libero_lora_pytorch --exp-name pi05_libero_lora_test
```

---

