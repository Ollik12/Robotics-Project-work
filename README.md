# Franka FR3 Environment for ROBO.666 FM Project

Docker-based ROS 2 development environment for the ROBO.666 FM project.
The environment provides a reproducible workspace for developing and testing the Franka Research 3 (FR3) with foundation models.

This environment uses the official `franka_ros2` package and its dependencies, along with `crisp_controllers` for CRISP-based VLA data collection and policy deployment.

This environment creates Docker workspace where the repository `src/` is mounted into Docker `ros2_ws/src`

> [!IMPORTANT]
> Environment has been found to work best with native Ubuntu. WSL can cause some unexpected issues.
> Tested with Ubuntu 24.04.5 LTS

## Prequisites
- Git
- Docker
- Visual Studio Code
- VS Code Dev Containers extension

## Setup

### Configure the shared Cyclone DDS network interface before starting shells

Docker and CRISP/Pixi use the same configuration file: [`src/cyclonedds.xml`](src/cyclonedds.xml). Docker accesses it at `/ros2_ws/src/cyclonedds.xml`; Pixi accesses it through `${PIXI_PROJECT_ROOT}/../src/cyclonedds.xml`.

After cloning the repository, configure this file **before reopening VS Code in the container, entering a Pixi shell, or launching ROS 2 nodes**. On each PC, use a host terminal to identify the interface connected to the network shared by the ROS PCs:

```bash
ip -br addr
```

Set that interface name in `src/cyclonedds.xml`. For example, for `eno1`:

```xml
<NetworkInterface name="eno1"/>
```

Docker uses host networking, so the host interface name also applies inside the container. Configure each PC's checkout for its own interface; names may differ between PCs.

### 1. Install Dev Contrainers extension to VS Code

### 2. Clone repository and open in VS Code
```
git clone git@github.com:Ollik12/Robotics-Project-work.git
cd Robotics-Project-work
code .
```
### 3. Dev Containers setup
- Complete the shared Cyclone DDS configuration above before opening the container.
- Choose `Reopen in container` when prompted in VS Code
- If you miss the prompt, press **Ctrl+Shift+P** to open the Command Palette, then select `Reopen in container`

#### NVIDIA GPU
- If you encounter problems with NVIDIA GPU e.g. Gazebo is not opened -> install **NVIDIA Container Toolkit**. Follow [these instructions](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) until 'Configuring Docker' header.
- When opening devcontainer choose `project_work_nvidia` devcontainer.json file to load NVIDIA specific Docker configuration

> [!NOTE]
> The first container startup may take a few minutes while the development environment is created.

### 4. Import dependencies (Franka + CRISP controllers)
```
vcs import src < dependency.repos --recursive --skip-existing
```

### 5. Install ROS2 dependencies
```
sudo apt update
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

### 6. Build all ROS2 packages
If you have problems with large colcon builds and container freezes
```
MAKEFLAGS="-j1" colcon build --executor sequential --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```
Otherwise you can just build with:
```
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

> [!IMPORTANT]
> When opening repository in VS Code and starting Dev Containers, make
> sure that you open it with `Reopen in container` **NOT** with `Rebuild and reopen in container`.
> If you rebuild the container you must install all the ROS2 dependencies again and build
> ROS2 packages from the scratch

## Launch Gazebo + RViz
The simulation includes a Franka Research 3 (FR3) robot in Gazebo and RViz.

Package is heavily based on the official franka_gazebo_bringup package but it has
been sligthly modified.

Franka FR3 uses `cartesian_impedance_controller` from `crisp_controllers`. Gazebo simulation also includes wrist and side camera.

Launch with:
```
ros2 launch franka_fm_gazebo sim.launch.py
```

## Launch real Franka/Environment ROS2 nodes with CRISP controllers

See the [Franka FM bringup instructions](./src/franka_fm_bringup/README.md). It includes more detailed instructions for launching the required nodes and also instructions for teleoperation.

Teleoperation and dataset recording requires `crisp` setup. See the [CRISP instructions](./crisp/README.md)

## RealSense camera configuration

See the [Franka FM Cameras](./src/franka_fm_cameras/README.md)

## Dataset recording workflow with real HW

Follow these steps in order. Keep each launched process running in its own terminal until recording is finished.

### Before starting

- Complete the [Docker/ROS 2 setup](#setup) and [CRISP/Pixi setup](./crisp/README.md), including the patch, environment configs, and teleoperation workspace build.
- Complete the [bringup configuration](./src/franka_fm_bringup/README.md#configuration), including camera setup, and select teleoperation `stream` mode as described in its [teleoperation section](./src/franka_fm_bringup/README.md#teleoperation).
- Connect the robot via Ethernet and confirm its IP address. Connect the gamepad and both cameras to the recording PC.

The instructions below use two PC roles, which may also be handled by one PC:

| Terminal | Where to run it | Purpose |
|---|---|---|
| A | Docker on the PC connected to the Franka | Robot controllers and gripper |
| B | Docker on the PC connected to the cameras | Wrist and side camera nodes |
| C | Host Pixi shell on the recording PC | Gamepad input and teleop stream |
| D | Host Pixi shell on the recording PC | Recording script and episode controls |

For each Docker terminal, use the built workspace at `/ros2_ws`. For each host terminal, start in your repository checkout; `crisp/` below is a repository-relative path, not `/crisp` at the filesystem root. Run Pixi **outside Docker**, activating it separately in terminals C and D.

### 1. Start the robot and gripper — terminal A

In Docker on the PC connected to the Franka:

```bash
cd /ros2_ws
source install/setup.bash
ros2 launch franka_fm_bringup franka_fm.launch.py robot_ip:=172.16.0.21 robot_type:=fr3 load_gripper:=true
```

Replace `172.16.0.21` with your robot's IP address. This starts the robot controllers, official Franka Hand action servers, and CRISP gripper adapter. Wait for bringup to complete before continuing.

### 2. Start both cameras — terminal B

In Docker on the PC with the cameras connected:

```bash
cd /ros2_ws
source install/setup.bash
ros2 launch franka_fm_cameras cameras.launch.py
```

If the cameras are connected to the robot PC, you can instead add `load_cameras:=true` to the command in step 1 and skip terminal B. Launch the cameras only once.

### 3. Start the gamepad teleop stream — terminal C

In a new host terminal on the recording PC, starting from the repository root:

```bash
cd crisp
pixi shell -e jazzy-lerobot
```

Once the Pixi shell is active:

```bash
cd ros2_ws
source install/setup.bash
ros2 launch crisp_teleop teleop.launch.py
```

Leave this running. In `stream` mode, this node publishes gamepad commands; the recording script in the next step connects them to robot control.

### 4. Start the recorder — terminal D

In another host terminal on the recording PC, starting from the repository root:

```bash
cd crisp
pixi shell -e jazzy-lerobot
```

Once the Pixi shell is active:

```bash
cd src/record
python3 record_teleop.py \
  --tasks 'Pick the green cube and place it on the blue surface' \
  --fps 15 \
  --num-episodes 2 \
  --repo-id green_cube_session_01
```

This example records two saved episodes at 15 FPS with the supplied task description. Choose a new `--repo-id` for each new dataset. The script uses the `franka_fm_real` environment configuration, which expects both wrist and side cameras. Uploading to Hugging Face is disabled by default.

Wait for `Recording manager is ready.` and the episode/task prompt before starting an episode. If initialization fails or times out, check terminals A–C for errors and run `ros2 topic list` from another host Pixi shell to check that robot, gripper, camera, and teleop topics are visible.

### 5. Record, review, and save each episode

Use the keyboard on the recording PC for recording controls and the gamepad for robot movement. Follow the prompts from terminal D.

1. Prepare the scene and objects for the task.
2. Press **`r`** to start an episode. The script resets the robot targets and calls the environment reset before collecting frames; be ready for robot movement.
3. Perform the task using the gamepad. Hold **L1** to enable teleoperation; see the [gamepad controls](./src/franka_fm_bringup/README.md#controls) for movement and gripper buttons.
4. Press **`r`** again to stop recording. The script commands the robot to return home before asking whether to save or discard the episode. Wait for the robot to finish moving before resetting the scene.
5. At the save/delete prompt, press **`s`** to save the episode or **`d`** to discard it. Discarded episodes do not count toward `--num-episodes`.
6. Reset the scene and repeat from step 2 until the requested number of episodes has been saved.

To finish early, save or discard the current episode, then press **`q`** while waiting for the next episode. After the requested episode count is reached, let the script finish writing the dataset and print `Finished recording.` before closing its terminal.

### 6. Locate the dataset and finish the session

Datasets are saved on the **recording PC** under the LeRobot cache directory. With the default cache settings, the example above writes to:

```text
~/.cache/huggingface/lerobot/green_cube_session_01/
```

If you omit `--repo-id`, its default is `test`, giving `~/.cache/huggingface/lerobot/test/`. The argument selects the dataset ID beneath the cache directory, rather than an arbitrary output path. Custom Hugging Face/LeRobot cache settings can change the base directory; the recorder logs the path to `meta/crisp_meta.json` during initialization.

For an existing dataset, use the same `--repo-id` with `--resume` and a `--num-episodes` value greater than the number already saved. Without `--resume`, an existing dataset directory causes initialization to fail; use a new ID to start a separate dataset.

Once the recorder has exited, stop the teleop, camera, and robot launch processes with **Ctrl+C** in their respective terminals. For uploading a completed dataset later, see the [manual Hugging Face upload instructions](./crisp/docs/workflows.md#upload-a-dataset).
