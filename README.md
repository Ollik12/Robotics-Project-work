# Franka FR3 Environment for ROBO.666 FM Project

Docker-based ROS 2 development environment for the ROBO.666 FM project.
The environment provides a reproducible workspace for developing and testing the Franka Research 3 (FR3) simulation and teleoperation software.

This environment uses the official `franka_ros2` package and its dependencies, along with `crisp_controllers` for future CRISP-based VLA data collection.

This environment creates Docker workspace where the repository `src/` is mounted into Docker `ros2_ws/src`

## Prequisites
- Git
- Docker
- Visual Studio Code
- VS Code Dev Containers extension

## Setup

### 1. Install Dev Contrainers extension to VS Code

### 2. Clone repository and open in VS Code
```
git clone git@github.com:Ollik12/Robotics-Project-work.git
cd Robotics-Project-work
code .
```
### 3. Dev Containers setup
- Choose `Reopen in container` when prompted in VS Code
- If you miss the prompt, press **Ctrl+Shift+P** to open the Command Palette, then select `Reopen in container`

The first container startup may take a few minutes while the development environment is created.

### 4. Import dependecies (franka + CRISP controllers)
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
> sure that you open it with `Reopen in container` NOT with `Rebuild and reopen in container`.
> If you rebuild the container you must install all the ROS2 dependencies again and build
> ROS2 packages from the scratch

## Launch Gazebo + RViz
The simulation includes a Franka Research 3 (FR3) robot in Gazebo and RViz.

Package is heavily based on the official franka_gazebo_bringup package but it has
been sligthly modified.

Franka FR3 uses `cartesian_impedance_controller` from `crisp_controllers`

Launch with:
```
ros2 launch franka_fm_gazebo sim.launch.py
```

## PS5 DualSense Teleoperation

The FR3 can be teleoperated using a PS5 DualSense controller.

### Controls

| Control                  | Function                               |
| ------------------------ | -------------------------------------- |
| **L1**                   | Enable teleoperation / dead-man switch |
| **Left stick — X axis**  | Move the robot left/ right             |
| **Left stick — Y axis**  | Move the robot up / down               |
| **Right stick — Y axis** | Move the robot up / down (Z)           |
| **X**                    | Close gripper                          |
| **O**                    | Open gripper                           |

### Stick Axis Mapping

* **Left stick vertical (Y)** → Cartesian **X** → forward / backward
* **Left stick horizontal (X)** → Cartesian **Y** → left / right
* **Right stick vertical (Y)** → Cartesian **Z** → up / down

### Known Issue

The gripper's `joint1` is controlled correctly, but in Gazebo `joint2` does not properly mimic the commanded movement. As a result, the gripper does not behave correctly in the Gazebo simulation.

The corresponding joint movement works as expected in RViz.

Start the simulation first, then launch the teleoperation node in a separate terminal:
```
ros2 run franka_fm_teleop ps5_teleop_node
```
The teleoperation node sends Cartesian motion commands to the robot through the ROS 2 control architecture.


## Keyboard teleoperation

The FR3 can be also teleoperated using a keyboard

### Controls

| Control                  | Function                               |
| ------------------------ | -------------------------------------- |
| **Spacebar**             | Enable teleoperation / dead-man switch |
| **W / S**                | Move the robot forward / backward (X)  |
| **A / D**                | Move the robot left / right (Y)        |
| **R / F**                | Move the robot up / down (Z)           |
| **O**                    | Close gripper                          |
| **P**                    | Open gripper                           |

Start the simulation first, then launch the teleoperation node in a separate terminal:
```
source install/setup.bash 
ros2 run franka_fm_teleop keyboard_teleop_node
```
The teleoperation node sends Cartesian motion commands to the robot through the ROS 2 control architecture with keyboard inputs

## Data Recorder

The `franka_fm_rec` package provides a simple ROS 2 bag recorder for collecting robot teleoperation episodes.

### Recorded topics
- `/wrist_camera/image`
- `/joint_states`
- `/target_pose`
- `/task`
- `/gripper_controller/commands`

Build and source the package:

```bash
colcon build --packages-select franka_fm_rec
source install/setup.bash
```

### Start the recorder
```
ros2 run franka_fm_rec bag_recorder_node
```

| Key | Action                   |
| --- | ------------------------ |
| `r` | Start a new episode      |
| `s` | Stop the current episode |
| `q` | Stop recording and quit  |


### Output

Bag files are saved to /src/franka_fm_rec/bags/ directory by default

Each episode is stored as a ROS 2 bag directory containing an MCAP file and metadata

Bags can be played inside the Docker container with
```
ros2 bag play /ros2_ws/src/franka_fm_rec/bags/<episode_name>
```

> [!NOTE]
> Remember to shut down teleoperation node if playing rosbag data.