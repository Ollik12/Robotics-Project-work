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

Franka FR3 uses `cartesian_impedance_controller` from `crisp_controllers`. Gazebo simulation also includes wrist and side camera.

Launch with:
```
ros2 launch franka_fm_gazebo sim.launch.py
```