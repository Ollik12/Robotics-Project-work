# OpenPI Installation

### 1. Clone the repository

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

### 2. Set up OpenPI

Build/rebuild the Docker container after cloning the OpenPI repository. See the [Docker setup instructions](https://github.com/Ollik12/Robotics-Project-work/blob/main/README.md).

### In Docker

Install `uv`:

```bash
cd /ros2_ws/openpi-fr3
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

Install the OpenPI dependencies inside the `openpi-fr3` folder:

```bash
GIT_LFS_SKIP_SMUDGE=1 uv sync
GIT_LFS_SKIP_SMUDGE=1 uv pip install -e .
```

### 3. Replace the configuration file

Replace the `config.py` file in `ros2_ws/openpi-fr3/openpi/src/openpi/training/config.py` with the provided configuration file from `ros2_ws/openpi-fr3/src/config.py`.
```bash
cp /ros2_ws/openpi-fr3/src/config.py /ros2_ws/openpi-fr3/openpi/src/openpi/training/config.py
```

### 4. Install the required Transformers version

Activate the OpenPI environment:

```bash
cd /ros2_ws/openpi-fr3
source .venv/bin/activate
```

Install and copy the transformers package.

```bash
uv pip install transformers==4.53.2
cp -r openpi/src/openpi/models_pytorch/transformers_replace/* .venv/lib/python3.11/site-packages/transformers/
```

### 5. Install the OpenPI client

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

# Gazebo Simulation + FR3 + PI0.5 Inference

**Note:** PI0.5 inference requires about 9 GB of VRAM.


### 1. Activate the OpenPI environment

In Docker terminal:

```bash
cd /ros2_ws/openpi-fr3
source .venv/bin/activate
```

You should now see `(openpi)` in the shell prompt.


### 2. Download the fine-tuned model 

Login to Hugging Face:
```bash
uv run hf auth login
```

Download the model:
```bash
uv run hf download otto-95/pi05-fr3-gz-lora
```

Set the model directory variable:
```bash
MODEL_DIR="$HOME/.cache/huggingface/hub/models--otto-95--pi05-fr3-gz-lora/snapshots/be9dda192efce20d77d4ff40d895fbe1075eff9d"
```

### 3. Start the OpenPI policy server

Start the OpenPI policy server:

```bash
uv run --project /ros2_ws/openpi-fr3 \
  python openpi/scripts/serve_policy.py \
  policy:checkpoint \
  --policy.config=pi05_libero_lora_pytorch \
  --policy.dir="$MODEL_DIR"
```

### 4. Start the FR3 simulation

Open a new Docker terminal and launch the gazebo sim:

```bash
ros2 launch franka_fm_gazebo sim.launch.py
```

### 5. Start the OpenPI ROS 2 node

In another Docker terminal, start the ROS 2 OpenPI inference node:

```bash
ros2 run openpi_ros openpi_inference
```

The node:

1. Receives camera images and the FR3 joint state from Gazebo.

2. Constructs the OpenPI observation.

3. Sends the observation to the OpenPI policy server for inference.

4. Receives the predicted action chunk.

5. Sends the actions to CRISP to control the robot.


### 6. Start the Crisp control script

Open a new terminal window in the host and activate the Pixi environment:

```bash
cd crisp
pixi shell -e jazzy-lerobot
```

Run the control script:

```bash
python src/scripts/openpi_pi05_control.py 
```

The Gazebo robot should now attempt to complete the task.

# LoRA Fine-tuning

**Note:** LoRA fine-tuning is recommended to be performed on a GPU with at least 16 GB of VRAM.

Make sure you have cloned the LoRA fine-tuning repository from `sen-code-lost`.

### 1. Download the pretrained model

Use the serve policy script to download the pretrained `pi05_libero` model:
```bash
uv run --project /ros2_ws/openpi-fr3 \
  python openpi/scripts/serve_policy.py \
  policy:checkpoint \
  --policy.config=pi05_libero \
  --policy.dir="gs://openpi-assets/checkpoints/pi05_libero"
```

### 2. Convert the JAX checkpoint to PyTorch

```bash
uv run uv run --project /ros2_ws/openpi-fr3 \
    python openpi/examples/convert_jax_model_to_pytorch.py \
    --config-name=pi05_libero \
    --checkpoint_dir="$HOME/.cache/openpi/openpi-assets/checkpoints/pi05_libero" \
    --output_path="$HOME/.cache/openpi/openpi-assets/checkpoints/pi05_libero_pytorch"
```

### 3. Compute the normalization statistics

```bash
uv run --project /ros2_ws/openpi-fr3 \
  python openpi/scripts/compute_norm_stats.py \
  --config-name=pi05_libero_lora_pytorch
```

### 4. Start LoRA fine-tuning

Before starting the training, you can change the hyperparameters in the `pi05_libero_lora_pytorch` `TrainConfig` in `openpi/src/openpi/training/config.py`.

```bash
uv run --project /ros2_ws/openpi-fr3 \
  python openpi/scripts/train_pytorch.py \
  pi05_libero_lora_pytorch \
  --exp-name pi05_libero_lora_test
```


