# CRISP / Pixi setup

This guide prepares the host environment for CRISP. Run these steps **outside Docker**: Pixi provides its own RoboStack ROS 2 installation. For robot package configuration, see [Franka FM bringup](../src/franka_fm_bringup/README.md); for the launch and recording sequence, use the [root recording workflow](../README.md#dataset-recording-workflow-with-real-hw).

## 1. Configure networking

Complete the [shared Cyclone DDS configuration](../README.md#configure-the-shared-cyclone-dds-network-interface-before-starting-shells) before entering Pixi. The activation script [`scripts/set_env.sh`](scripts/set_env.sh) sets `ROS_DOMAIN_ID=100`, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, and `CYCLONEDDS_URI` to the shared XML file. Docker must use the same domain and middleware.

## 2. Install Pixi and clone the dependency

Install Pixi on the host:

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Open a new host terminal after installation. From the repository root:

```bash
cd crisp
git clone https://github.com/learnsyslab/crisp_gym.git
```

Skip the clone if `crisp/crisp_gym` already exists. The remaining setup commands start from `crisp/`.

## 3. Activate and verify the environment

```bash
pixi shell -e jazzy-lerobot
```

The first activation installs the dependencies, requiring approximately 13 GB. In the activated shell, verify both imports:

```bash
python -c "import crisp_gym"
python -c "import crisp_py"
```

Both commands should exit without errors. Activate this environment separately in every host terminal used for CRISP.

## 4. Apply the recording patch and install environment configs

From `crisp/`, copy the supplied recording patch and environment configurations:

```bash
cp patches/record_functions.py crisp_gym/crisp_gym/record/record_functions.py
cp src/config/envs/franka_fm_real.yaml crisp_gym/crisp_gym/config/envs/
cp src/config/envs/franka_fm_sim.yaml crisp_gym/crisp_gym/config/envs/
cp src/config/envs/franka_fm_no_cameras.yaml crisp_gym/crisp_gym/config/envs/
```

The patch fixes streamed teleoperation's gripper access. These commands replace the corresponding files in the local `crisp_gym` checkout; repeat the relevant copy after changing a source configuration.

| Environment | Intended use |
|---|---|
| `franka_fm_real` | Real robot with wrist and side cameras; selected by `src/record/record_teleop.py` |
| `franka_fm_sim` | Simulation with cameras |
| `franka_fm_no_cameras` | Real robot without cameras |

## 5. Build the teleoperation workspace

In the activated Pixi shell, from `crisp/`:

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

In every new Pixi shell that will launch `crisp_teleop`, source `crisp/ros2_ws/install/setup.bash` before launching the node. Configure the gamepad using the [teleoperation configuration](../src/franka_fm_bringup/README.md#teleoperation) before recording.

Setup is complete. Continue with the [dataset recording workflow](../README.md#dataset-recording-workflow-with-real-hw) or the separate [upload, inference, and training guide](docs/workflows.md).
