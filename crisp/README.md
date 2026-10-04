# CRISP Setup

> [!NOTE]
> `crisp_gym` will run inside Pixi environment with dedicated Robostack ROS2 version. Therefore, setup/run crisp outside the Franka Docker environment. CRISP and the Franka Docker ROS will communicate with each other via same `ROS_DOMAIN_ID`.

## 1. Install Pixi

Linux
```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

## 2. Clone `crisp_gym` 

Navigate to `crisp` directory and clone the `crisp_gym` repository
```bash
cd crisp
git clone git@github.com:learnsyslab/crisp_gym.git
cd crisp_gym
```

## 3. Create `set_env.sh` script

Navigate to `scripts` directory inside `crisp_gym`
```bash
cd scripts
touch set_env.sh
```

Add the following content into the script:
```bash
export GIT_LFS_SKIP_SMUDGE=1  
export SVT_LOG=1  
export ROS_DOMAIN_ID=100
```

## 4. Modify `pixi.toml`

Find `[feature.lerobot.pypi-dependencies]` from `pixi.toml` file and make it similar to this:
```toml
[feature.lerobot.pypi-dependencies]
# === Working version ===
lerobot = { git = "https://github.com/huggingface/lerobot", rev = "dacd1d7f5c719c3e56d7b7154a751bef6d5bd23c", extras = ["smolvla"]}
# === Newer version ===
# lerobot = { git = "https://github.com/huggingface/lerobot", rev = "74690e3f56a90b6ea314afbfb3b801a3d842a005", extras = ["smolvla"]}
# === Local version ===
# lerobot = { path = "../clare_rebuttal/lerobot_lsy/", editable = true }
```

We use ROS2 Jazzy, so configure also:
```toml
[environments]
dev = { features = ["dev"] }
humble = { features = ["humble"] }
humble-lerobot = { features = ["humble", "lerobot", "dev"] }
lerobot = { features = ["lerobot"] }
jazzy = { features = ["jazzy"] }
jazzy-lerobot = { features = ["jazzy", "lerobot", "dev"] }
```

## 5. Add `crisp_py` to dependencies

`crisp_py` can be added to dependencies with:
```bash
pixi add --pypi crisp-python
```

## 6. Install `crisp_gym`

Install Pixi environment with:
```bash
GIT_LFS_SKIP_SMUDGE=1 pixi install -e jazzy-lerobot
```

## 7. Access Pixi shell and test installation

Access the CRISP Pixi shell with:
```bash
pixi shell -e jazzy-lerobot
```

Test that the installation was successful. These should not print anything:
```bash
python -c "import crisp_gym"
python -c "import crisp_py"
```

## Teleoperation with CRISP

> [!NOTE]
> This currently works only with PS5 teleoperation but will be implemented for other teleoperation devices too (HTC Vive, keyboard etc.). This is currently just a small script/PoC implementation which verifies that Gazebo Franka can be controlled with CRISP.

### 1. Set `ROS_DOMAIN_ID`
(Fix: Docker environment should be started with ROS_DOMAIN_ID=100)

Currently Docker environment has no `ROS_DOMAIN_ID`, but the Pixi ROS2 Jazzy is started with `ROS_DOMAIN_ID=100`. We can set our Docker environment to the same domain. In Docker terminal run:
```bash
export ROS_DOMAIN_ID=100
```

### 2. Copy config

Copy the config `franka_fm.yaml` included in `crisp/src/config/envs` to the `crisp_gym/crisp_gym/config/envs` directory

### 3. Run Gazebo

In Docker terminal run the Gazebo simulation environment with:
```bash
ros2 launch franka_fm_gazebo sim.launch.py
```


### 4. Run PS5 teleop node

In another Docker terminal launch PS5 teleop node with `--crisp-teleop` argument
```bash
ros2 run franka_fm_teleop ps5_teleop_node --crisp-teleop
```

### 5. Run CRISP teleop script

Finally, run in Pixi/CRISP terminal script which is located in `crisp/src/teleop/crisp_teleop.py`. Navigate to that directory in your terminal and run:
```bash
python crisp_teleop.py
```

It should print these is everything is OK and then the teleoperation should work:
```
Environment created
Target initialized
Teleop is ready
```

## 📝 TODO:
- Implement CRISP teleoperation nodes for other devices such as HTC Vive, 3D Mouse, keyboard etc. / whatever device we will use for teleoperating the real Franka in the future
- Implement script with teleop and dataset recording functionality using `crisp_gym` `RecordingManager`. Similar to `crisp_gym/crisp_gym/scripts/record_lerobot_format_leader_follower.py`
- Include image topics in dataset recorder script (i.e. include cameras in CRISP environment config)
- Record dataset using Gazebo and CRISP and successfully push it into Hugging Face dataset repository
