# Franka FM Bringup

ROS 2 bringup package for the Franka Research 3 (FR3) robot using the CRISP Cartesian Impedance Controller.

The package extends the standard `franka_bringup` launch configuration with custom controller settings.

## Description

The `franka_fm.launch.py` launch file starts:

- **Franka Bringup:** Initializes the robot hardware interface and ROS 2 Control Manager.
- **Cartesian Impedance Controller:** CRISP controller for Cartesian motion control.
- **Pose Broadcaster:** Publishes the robot's current end-effector pose.

## Usage

Launch the robot with:

```bash
ros2 launch franka_fm_bringup franka_fm.launch.py robot_ip:=172.16.0.2 robot_type:=fr3
```

Ensure the robot is connected and ready before launching.

## Teleoperation

The FR3 robot can be teleoperated using a PS5 DualSense controller through the `crisp_teleop` ROS 2 package.

The teleop node uses `crisp_py.Robot` to send Cartesian target poses to the CRISP Cartesian Impedance Controller.

### Setup

1. Connect the PS5 controller to the computer.

2. **Outside Docker**, navigate to the `crisp` directory and activate the Pixi environment:

   ```bash
   pixi shell -e jazzy-lerobot
   ```

3. Navigate to the ROS 2 workspace:

   ```bash
   cd ros2_ws
   ```

4. Build the packages if not already built:

   ```bash
   colcon build --symlink-install
   ```

5. Source the workspace:

   ```bash
   source install/setup.bash
   ```

### Launch Teleoperation

Ensure the FR3 robot and CRISP Cartesian Impedance Controller are running before starting teleoperation.

```bash
ros2 launch crisp_teleop teleop.launch.py
```

The launch file starts:
- **Joy Node:** Reads input from the PS5 controller and publishes `/joy` messages.
- **CRISP Teleop Node:** Processes joystick inputs and sends Cartesian target poses to the robot using `crisp_py.Robot`.

### Controls

| PS5 Input | Function |
|---|---|
| L1 (hold) | Enable teleoperation (deadman switch) |
| Left stick | Move end-effector along X/Y axes |
| L2 / R2 | Move end-effector along Z axis |
| Right stick | Control end-effector orientation |
| X | Close gripper (optional) |
| O | Open gripper (optional) |

**Safety:** Teleoperation requires holding L1. Release L1 to disable new motion commands. This software deadman is not a safety-rated stop; ensure the robot's emergency stop and safety procedures are available.