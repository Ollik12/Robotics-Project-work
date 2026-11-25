import time

import numpy as np
import rclpy

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Joy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32

from scipy.spatial.transform import Rotation

from crisp_py.robot.robot import make_robot
from crisp_py.utils.geometry import Pose

class PS5TeleopNode(Node):

    def __init__(self):
        super().__init__("crisp_teleop")

        # Control parameters
        self.declare_parameter("update_rate", 30.0)
        self.declare_parameter("trans_speed", 0.05)
        self.declare_parameter("rot_speed", 0.1)
        self.declare_parameter("deadzone", 0.1)
        self.declare_parameter("mode", "robot")

        # Safety parameters
        self.declare_parameter("joy_timeout", 0.2)

        # Controller mapping
        self.declare_parameter("axis_left_x", 0)
        self.declare_parameter("axis_left_y", 1)
        self.declare_parameter("axis_right_x", 3)
        self.declare_parameter("axis_right_y", 4)
        self.declare_parameter("axis_l2", 2)
        self.declare_parameter("axis_r2", 5)
        self.declare_parameter("button_deadman", 4)
        self.declare_parameter("button_x", 0)
        self.declare_parameter("button_o", 1)

        # Read parameters
        self.update_rate = self.get_parameter("update_rate").value
        self.trans_speed = self.get_parameter("trans_speed").value
        self.rot_speed = self.get_parameter("rot_speed").value
        self.deadzone = self.get_parameter("deadzone").value
        self.mode = self.get_parameter("mode").value
        self.joy_timeout = self.get_parameter("joy_timeout").value

        if self.mode not in ("robot", "stream"):
            raise ValueError(
                f"Unsupported teleop mode '{self.mode}'. Expected 'robot' or 'stream'."
            )

        self.axis_left_x = self.get_parameter("axis_left_x").value
        self.axis_left_y = self.get_parameter("axis_left_y").value
        self.axis_right_x = self.get_parameter("axis_right_x").value
        self.axis_right_y = self.get_parameter("axis_right_y").value
        self.axis_l2 = self.get_parameter("axis_l2").value
        self.axis_r2 = self.get_parameter("axis_r2").value
        self.button_deadman = self.get_parameter("button_deadman").value
        self.button_x = self.get_parameter("button_x").value
        self.button_o = self.get_parameter("button_o").value

        self.namespace = self.get_namespace().strip("/")

        self.robot = None
        self.current_pose = None
        self.current_pose_frame_id = ""
        if self.mode == "robot":
            self.robot = make_robot("fr3", namespace=self.namespace)
            self.robot.wait_until_ready()

        # Joystick state
        self.joy_axes = [0.0] * 6
        self.enabled = False
        self.joy_received = False
        self.last_joy_time = None
        self.deadman_released = False
        self.active = False

        self.target_pose = None
        self.gripper_value = 0.0

        self.pose_pub = None
        self.gripper_pub = None
        if self.mode == "stream":
            self.current_pose_sub = self.create_subscription(
                PoseStamped,
                "/current_pose",
                self.current_pose_callback,
                qos_profile_sensor_data,
            )
            self.pose_pub = self.create_publisher(
                PoseStamped,
                "/phone_pose",
                qos_profile_sensor_data,
            )
            self.gripper_pub = self.create_publisher(
                Float32,
                "/phone_gripper",
                qos_profile_sensor_data,
            )

        # Subscribers
        self.joy_sub = self.create_subscription(
            Joy,
            "/joy",
            self.joy_callback,
            qos_profile_sensor_data,
        )

        # Control timer
        self.timer = self.create_timer(
            1.0 / self.update_rate,
            self.update,
        )

        self.get_logger().info("CRISP Teleop initialized")

    def joy_callback(self, msg: Joy):
        required_axes = [
            self.axis_left_x,
            self.axis_left_y,
            self.axis_right_x,
            self.axis_right_y,
            self.axis_l2,
            self.axis_r2,
        ]

        if (
            any(i < 0 or i >= len(msg.axes) for i in required_axes)
            or self.button_deadman < 0
            or self.button_deadman >= len(msg.buttons)
            or self.button_x < 0
            or self.button_x >= len(msg.buttons)
            or self.button_o < 0
            or self.button_o >= len(msg.buttons)
        ):
            return

        self.last_joy_time = time.monotonic()
        self.joy_received = True

        self.joy_axes = [
            msg.axes[self.axis_left_x],
            msg.axes[self.axis_left_y],
            msg.axes[self.axis_l2],
            msg.axes[self.axis_r2],
            msg.axes[self.axis_right_x],
            msg.axes[self.axis_right_y],
        ]

        self.enabled = bool(msg.buttons[self.button_deadman])

        if msg.buttons[self.button_x]:
            self.gripper_value = 0.0
        elif msg.buttons[self.button_o]:
            self.gripper_value = 1.0

        if not self.enabled:
            self.deadman_released = True

    def current_robot_pose(self):
        if self.mode == "robot":
            return self.robot.end_effector_pose
        if self.current_pose is None:
            return None
        return self.current_pose.copy()

    def current_pose_callback(self, msg: PoseStamped):
        self.current_pose = Pose.from_ros_msg(msg)
        self.current_pose_frame_id = msg.header.frame_id

    def send_target(self):
        if self.mode == "robot":
            self.robot.set_target(pose=self.target_pose)
            return

        pose_msg = self.target_pose.to_ros_msg(
            self.current_pose_frame_id,
            self.get_clock().now().to_msg(),
        )
        self.pose_pub.publish(pose_msg)

        gripper_msg = Float32()
        gripper_msg.data = self.gripper_value
        self.gripper_pub.publish(gripper_msg)

    def apply_deadzone(self, value):
        if abs(value) < self.deadzone:
            return 0.0

        sign = np.sign(value)

        return sign * (
            (abs(value) - self.deadzone) /
            (1.0 - self.deadzone)
        )

    def update(self):
        measured_pose = self.current_robot_pose()
        if measured_pose is None:
            return

        # Initialize target from actual robot pose
        if self.target_pose is None:
            self.target_pose = measured_pose
            self.send_target()
            self.get_logger().info("Teleop target initialized")

        # Communication timeout
        joy_valid = (
            self.joy_received
            and time.monotonic() - self.last_joy_time
            < self.joy_timeout
        )

        if not joy_valid:
            self.active = False
            self.deadman_released = False
            self.enabled = False

            # Hold the current measured pose
            self.target_pose = measured_pose
            self.send_target()
            return

        # Deadman released
        if not self.enabled:
            self.active = False

            self.target_pose = measured_pose
            self.send_target()
            return

        # Require a deadman release before activation
        if not self.deadman_released:
            return

        # Synchronize target when control is activated
        if not self.active:
            self.target_pose = measured_pose
            self.send_target()
            self.active = True
            return

        # Read joystick inputs
        x_input = self.apply_deadzone(self.joy_axes[0])
        y_input = self.apply_deadzone(self.joy_axes[1])

        yaw_input = self.apply_deadzone(self.joy_axes[4])
        pitch_input = self.apply_deadzone(self.joy_axes[5])

        l2_input = self.joy_axes[2]
        r2_input = self.joy_axes[3]

        # PS5 triggers: released = 1, pressed = -1
        l2 = (1.0 - l2_input) / 2.0
        r2 = (1.0 - r2_input) / 2.0

        z_input = r2 - l2

        # Calculate Cartesian increments
        dt = 1.0 / self.update_rate

        dx = y_input * self.trans_speed * dt
        dy = x_input * self.trans_speed * dt
        dz = z_input * self.trans_speed * dt

        dyaw = yaw_input * self.rot_speed * dt
        dpitch = pitch_input * self.rot_speed * dt

        # Update target position
        self.target_pose.position += np.array([
            dx, dy, dz
        ])

        # Update target orientation
        delta_rotation = Rotation.from_euler(
            "xyz",
            [0.0, dpitch, dyaw],
        )

        self.target_pose.orientation = (
            delta_rotation * self.target_pose.orientation
        )

        # Send target to CRISP Robot
        self.send_target()

def main(args=None):
    rclpy.init(args=args)

    node = None

    try:
        node = PS5TeleopNode()
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        if node is not None:
            if node.mode == "robot":
                # Remove application targets before shutdown.
                # This is not a guaranteed hardware stop.
                node.robot.reset_targets()
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()