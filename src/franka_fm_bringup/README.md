# Franka FM Bringup

ROS 2 bringup package for the Franka Research 3 (FR3) robot using the CRISP Cartesian Impedance Controller.

The package extends the standard `franka_bringup` launch configuration with custom controller settings and optional Franka Hand support.

## Description

The `franka_fm.launch.py` launch file starts:

- **Franka Bringup:** Initializes the robot hardware interface and ROS 2 Control Manager.
- **Cartesian Impedance Controller:** CRISP controller for Cartesian motion control.
- **Pose Broadcaster:** Publishes the robot's current end-effector pose.
- **Franka Gripper (optional):** Launches the official `franka_gripper` action servers for controlling the Franka Hand.
- **Franka Hand CRISP Adapter (optional):** Launches `franka_hand_crisp_py_adapter`, which translates CRISP gripper commands into actions supported by the official Franka gripper driver.
- **Camera Nodes (optional)** Launches `franka_fm_cameras`, which starts two RealSense Camera nodes automatically. See [Franka FM Cameras](../franka_fm_cameras/README.md) for further instructions how to configure cameras etc.

Both optional gripper components are launched when `load_gripper:=true` is specified.

Camera nodes are launched when `load_cameras:=true` is specified.

### Gripper Control

The Franka Hand is controlled through the official `franka_gripper` action servers instead of a ROS 2 position controller.

The `franka_hand_crisp_py_adapter` package provides compatibility with CRISP by subscribing to gripper position commands and forwarding them to the appropriate Franka Hand action servers.

The adapter uses the following interfaces:

| Interface | Description |
|---|---|
| `/gripper/gripper_position_controller/commands` | Receives gripper commands from CRISP |
| `/gripper/joint_states` | Receives/updates gripper joint states |
| `/franka_gripper/grasp` | Franka Hand grasp action server |
| `/franka_gripper/homing` | Franka Hand homing action server |

## Configuration

Complete the [Docker workspace setup](../../README.md#setup) and [shared network configuration](../../README.md#configure-the-shared-cyclone-dds-network-interface-before-starting-shells) first. Run this package in Docker on the PC connected to the robot. Confirm the robot is ready and use its actual Ethernet IP address.

### Launch arguments

Pass overrides as `argument:=value` to `franka_fm.launch.py`.

| Argument | Default | Purpose |
|---|---|---|
| `robot_type` | Empty | Set to `fr3` for this robot |
| `robot_ip` | `172.16.0.2` | Robot IP address; set explicitly for your hardware |
| `load_gripper` | `false` | Start the Franka Hand driver and CRISP adapter |
| `load_cameras` | `false` | Start both RealSense nodes on the machine running bringup |
| `controllers_yaml` | Package `config/controllers.yaml` | Override the ROS 2 controller configuration file |
| `namespace` | Empty | ROS namespace for the robot |
| `arm_prefix` | Empty | Prefix for arm topics |
| `joint_state_rate` | `30` | Joint state publishing rate in Hz |
| `load_franka_robot_state_broadcaster` | `true` | Enable the Franka robot state broadcaster |
| `use_fake_hardware` | `false` | Use fake hardware instead of the physical robot |
| `fake_sensor_commands` | `false` | Enable fake sensor commands |

Keep the default empty namespace and arm prefix for the supplied CRISP recording configuration. If you change them, update the corresponding CRISP topic configuration to match.

### Controllers

The default controller configuration is [`config/controllers.yaml`](config/controllers.yaml). Use `controllers_yaml:=/absolute/path/to/controllers.yaml` to select a different file visible inside Docker. Check this file when configuring controller parameters.

### Cameras

Configure camera serial numbers and image profiles using the [camera package instructions](../franka_fm_cameras/README.md#configuration). Enable `load_cameras:=true` only when the cameras are connected to the bringup PC. For cameras on another PC, leave it disabled and launch the camera package there as described in the root workflow.

## Usage

The complete [real-hardware recording workflow](../../README.md#dataset-recording-workflow-with-real-hw) contains the ordered launch commands, terminal assignments, and recording controls. Its robot launch command can be adapted using the arguments above; for example, omit `load_gripper:=true` when operating without the hand.

## Teleoperation

The FR3 robot can be teleoperated using a PS5 DualSense controller through the `crisp_teleop` ROS 2 package.

> [!NOTE]
> Teleop node can be configured to publish commands to `/phone_pose` & `/phone_gripper` topics which is required
> when we are using CRISP environment for recording dataset episodes.

Ensure that `teleop.yaml` in `crisp/ros2_ws/src/crisp_teleop/config` is configured as:
```yaml
mode: "stream"  # "stream" or "robot"
```

If you want to just test the teleoperation without CRISP environment, you can configure the `teleop.yaml` mode to `robot` (no gripper control)

- The direct robot mode uses `crisp_py.Robot` to send Cartesian target poses to the CRISP Cartesian Impedance Controller.
- Stream mode publishes commands which are conveyed to CRISP environment through CRISP `TeleopStreamedPose` (this is the preferred way since this environment is primarily used for recording datasets with CRISP).

### Setup

Connect the gamepad and complete the [Pixi setup and teleoperation workspace build](../../crisp/README.md). Gamepad mappings, speed, deadzone, and timeout settings are defined in [`teleop.yaml`](../../crisp/ros2_ws/src/crisp_teleop/config/teleop.yaml).

### Launch Teleoperation

Follow the [root workflow](../../README.md#dataset-recording-workflow-with-real-hw) to launch the gamepad node and recorder in separate host Pixi shells. The gamepad launch starts the Joy node and CRISP teleop node. In `stream` mode, the recorder consumes the published commands.

For teleoperation without recording, use `crisp/src/teleop/crisp_teleop.py` as the stream consumer instead of the recorder. With the robot and gamepad node running, activate a separate Pixi shell, navigate to `crisp/src/teleop`, and run:

```bash
python3 crisp_teleop.py
```

Check the environment selected in that script before using it with your hardware.

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
