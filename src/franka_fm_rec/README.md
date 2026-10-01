# Data recorder package

The `franka_fm_rec` package provides a simple ROS 2 bag recorder for collecting robot teleoperation episodes.

### Recorded topics
- `/wrist_camera/image/compressed`
- `side_camera/image/compressed`
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

Bag files are saved into /src/franka_fm_rec/bags/ directory by default

Each episode is stored as a ROS 2 bag directory containing an MCAP file and metadata

Bags can be played inside the Docker container with
```bash
ros2 bag play /ros2_ws/src/franka_fm_rec/bags/<episode_name>
```
Playback speed can be changed with parameter `--rate` e.g. `--rate 0.5`

Image data can be monitored via rqt:
```bash
rqt
```
Select from Plugins > Visualization > Image View

Play the rosbag data and select the image topic you want to display.

> [!NOTE]
> Remember to shut down teleoperation node if playing rosbag data and you want to inspect the movement in simulation. Teleop node will overwrite the /target_pose.