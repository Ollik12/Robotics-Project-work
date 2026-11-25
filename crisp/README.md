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
cp patches/lerobot_features.py crisp_gym/crisp_gym/util/lerobot_features.py
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

### Side-camera workspace mask

The `franka_fm_real` environment masks its side-camera images to the polygon
formed by four ArUco marker centers. Configure `workspace_aruco_ids` in
`src/config/envs/franka_fm_real.yaml` with the four printed IDs, in order around
the field boundary, and set `workspace_aruco_dictionary` to the dictionary
used to generate those markers. The defaults are IDs `0, 1, 2, 3` from
`DICT_4X4_50`; replace them if the physical markers differ.

Keep the side camera fixed and make all four markers visible when the camera
node starts. The side camera is not ready until that initial calibration
succeeds, and uncalibrated frames are black. Afterward the calibrated polygon
is retained if a marker is covered during an episode, so occlusion does not
change the workspace boundary. Pixels outside the polygon are set to black.
The wrist camera is not processed. Re-copy the real environment config to the
local `crisp_gym` checkout after changing the IDs.

To identify and save the marker IDs, first start the side camera as described
in the recording workflow, then run this from a Pixi `jazzy-lerobot` shell in
`crisp/`:

```bash
python src/scripts/calibrate_aruco_workspace.py --write-config
```

The preview labels each detected tag. Click a tag and press `1` through `4` to
assign positions clockwise around the workspace, starting at any corner. Press
`s` to save the four unique IDs to `src/config/envs/franka_fm_real.yaml`; press
`r` to clear the assignments or `q` to quit. Without `--write-config`, the
script prints the YAML values without changing the file. After saving, copy the
updated real config into the local `crisp_gym` checkout as described above.

## 5. Build the teleoperation workspace

In the activated Pixi shell, from `crisp/`:

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

In every new Pixi shell that will launch `crisp_teleop`, source `crisp/ros2_ws/install/setup.bash` before launching the node. Configure the gamepad using the [teleoperation configuration](../src/franka_fm_bringup/README.md#teleoperation) before recording.

Setup is complete. Continue with the [dataset recording workflow](../README.md#dataset-recording-workflow-with-real-hw) or the separate [upload, inference, and training guide](docs/workflows.md).
