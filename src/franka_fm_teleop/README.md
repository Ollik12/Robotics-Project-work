# Teleoperation package

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