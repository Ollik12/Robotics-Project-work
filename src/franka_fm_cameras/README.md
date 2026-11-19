# Franka FM Cameras

ROS 2 camera bringup package for two Intel RealSense cameras used with the Franka Research 3 (FR3) robot.

## Description

The package launches two RealSense camera nodes using the official `realsense2_camera` ROS 2 driver:

- **Wrist camera:** Mounted near the robot end effector.
- **Side camera:** Provides an external view of the workspace.

Both cameras are configured to publish RGB images at 640×480 resolution and 30 FPS. Depth streaming is disabled by default.

## Configuration

Camera settings are defined in `config/cameras.yaml`.

```yaml
wrist_camera:
  serial_no: ""
  color_profile: "640x480x30"

side_camera:
  serial_no: ""
  color_profile: "640x480x30"
```

Before using physical cameras, identify their serial numbers:

```bash
rs-enumerate-devices -s
```

Update the `serial_no` values to ensure each camera is assigned to the correct node.
ROS 2 RealSense wrapper requires an underscore (_) prefix before numeric serial numbers. For example serial 1234 config:
```yaml
wrist_camera:
  serial_no: "_1234"
  color_profile: "640x480x30"
```

## ROS2 dependencies

The`compressed_image_transport` plugin is required to publish compressed images for CRISP.

Install dependencies if not already installed:
```bash
sudo apt update
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

## Usage

### Standalone

Launch both cameras independently:

```bash
ros2 launch franka_fm_cameras cameras.launch.py
```

## ROS 2 Topics

The cameras publish RGB images to:

```text
/camera/wrist_camera/color/image_raw
/camera/wrist_camera/color/image_raw/compressed
/camera/side_camera/color/image_raw
/camera/side_camera/color/image_raw/compressed
```

These topics can be used by the CRISP recording environment to collect camera observations.

## Dependencies

- ROS 2 Jazzy
- `realsense2_camera`
- `librealsense2`

The RealSense SDK and ROS 2 wrapper must be installed before launching the cameras. (They are installed when Docker image is built)