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

### Configure Docker side `cyclonedds.xml`:

We must configure CycloneDDS so that two PCs in the same network can see each other's topics.

Check what network interface is used:
```bash
ip -br addr
```

In `src/cyclonedds.xml` if e.g. interface name is `eno1`, configure:
```xml
<NetworkInterface name="eno1"/>
```

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

See the [Franka FM bringup instructions](./src/franka_fm_bringup/README.md). It includes instructions for launching the required nodes and also instructions for teleoperation. 

Teleoperation and dataset recording requires `crisp` setup. See the [CRISP instructions](./crisp/README.md)

## RealSense camera configuration

See the [Franka FM Cameras](./src/franka_fm_cameras/README.md)
