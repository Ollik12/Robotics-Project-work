import sys

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Joy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float64MultiArray, Float32
from rclpy.qos import qos_profile_sensor_data


class PS5TeleopNode(Node):

    def __init__(self):
        super().__init__("ps5_teleop_node")

        self._use_crisp_teleop = False

        if '--crisp-teleop' in sys.argv:
            self._gripper_topic = "/phone_gripper" # Publish for CRISP teleop
            self._target_pose_topic = "/phone_pose" # Publish for CRISP teleop
            self._gripper_open_value = 1.0
            self._gripper_close_value = 0.0
            self._use_crisp_teleop = True
            self._crisp_gripper_msg_value = 0.0 # Initially 0 = close
            self._gripper_msg_type = Float32
        else: # Publish straight to the robot for Franka teleop
            self._gripper_topic = "/gripper_position_controller/commands"
            self._target_pose_topic = "/target_pose"
            self._gripper_open_value = 0.035
            self._gripper_close_value = 0.0
            self._gripper_msg_type = Float64MultiArray

        # Parameters
        self.deadzone = 0.1
        self.trans_speed = 0.1       # m/s
        self.rot_speed = 0.2         # rad/s
        self.update_rate = 100.0 # Hz

        # Joystick state
        self.joy_axes = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # [left_stick_x, left_stick_y, l2_axis, r2_axis, right_stick_x, right_stick_y]
        self.enabled = False

        # Target pose
        self.target_pose = None

        self.gripper_close = False
        self.gripper_open = False

        # Subscribers
        self.joy_sub = self.create_subscription(
            Joy,
            "/joy",
            self.joy_callback,
            qos_profile=qos_profile_sensor_data,
        )

        self.ee_pose_sub = self.create_subscription(
            PoseStamped,
            "/current_pose",
            self.ee_pose_callback,
            qos_profile=qos_profile_sensor_data,
        )

        # Pose publisher
        self.target_pose_pub = self.create_publisher(
            PoseStamped,
            self._target_pose_topic,
            10,
        )

        # Gripper control publisher
        self.gripper_pub = self.create_publisher(
            self._gripper_msg_type,
            self._gripper_topic,
            qos_profile=qos_profile_sensor_data,
        )


        # 30 Hz update timer
        self.timer = self.create_timer(
            1.0 / self.update_rate,
            self.update,
        )

        self.get_logger().info("Teleop node started.")

    def joy_callback(self, msg: Joy):
        # Left stick
        self.joy_axes[0] = msg.axes[0]  # Left stick horizontal axis -> controls robot y-axis (left/right)
        self.joy_axes[1] = msg.axes[1]  # Left stick vertical axis -> controls robot x-axis (forward/backward)

        # Right stick
        self.joy_axes[4] = msg.axes[3]  # Right stick horizontal axis -> controls robot yaw (turn left/right)
        self.joy_axes[5] = msg.axes[4]  # Right stick vertical axis -> controls robot pitch (tilt up/down)

        # L1
        self.enabled = bool(msg.buttons[4])

        # L2
        self.joy_axes[2] = msg.axes[2]  # L2 axis -> controls robot z-axis (up/down)
        # R2
        self.joy_axes[3] = msg.axes[5]  # R2 axis
        
       
        if not (self._use_crisp_teleop):
            # X
            self.gripper_close = bool(msg.buttons[0])
            # O
            self.gripper_open = bool(msg.buttons[1])
        else:
            # Update gripper flags for continuous publishing
            if msg.buttons[0]:
                self._crisp_gripper_msg_value = self._gripper_close_value
            elif msg.buttons[1]:
                self._crisp_gripper_msg_value = self._gripper_open_value

    def ee_pose_callback(self, msg: PoseStamped):
        # Initialize target pose from current robot pose
        if self.target_pose is None:
            self.target_pose = PoseStamped()
            self.target_pose.header = msg.header
            self.target_pose.pose = msg.pose

            self.get_logger().info("Initial target pose received.")

    def apply_deadzone(self, value):
        if abs(value) < self.deadzone:
            return 0.0

        # Rescale value so movement starts smoothly after deadzone
        sign = 1.0 if value > 0.0 else -1.0
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)

    def update(self):
        if self.target_pose is None:
            return

        if not self._use_crisp_teleop and not self.enabled:
            return
        
        # Stream current target pose and gripper commands, but do not update it if dead-man switch is not pressed
        elif self._use_crisp_teleop and not self.enabled:
            # Update timestamp
            self.target_pose.header.stamp = self.get_clock().now().to_msg()
            # Publish target
            self.target_pose_pub.publish(self.target_pose)

            gripper_msg = self._gripper_msg_type()

            gripper_msg.data = float(self._crisp_gripper_msg_value)
            self.gripper_pub.publish(gripper_msg)

            return

        # Apply deadzone
        x_input = self.apply_deadzone(self.joy_axes[0])
        y_input = self.apply_deadzone(self.joy_axes[1])

        yaw_input = self.apply_deadzone(self.joy_axes[4])
        pitch_input = self.apply_deadzone(self.joy_axes[5])

        l2_input = self.joy_axes[2]
        r2_input = self.joy_axes[3]

        if (l2_input < r2_input):
            if (l2_input >0.0):
                z_input = -l2_input  # L2 pressed -> move down
            else:
                z_input = l2_input  # L2 pressed -> move down

        elif (r2_input < l2_input):
            if (r2_input < 0.0):
                z_input = -r2_input  # R2 pressed -> move up
            else:
                z_input = r2_input  # R2 pressed -> move up

        else:
            z_input = 0.0  # No vertical movement
       
        # Convert joystick input to position increment
        dt = 1.0 / self.update_rate

        dx = y_input * self.trans_speed * dt
        dy = x_input * self.trans_speed * dt
        dz = z_input * self.trans_speed * dt

        dyaw = yaw_input * self.rot_speed * dt
        dpitch = pitch_input * self.rot_speed * dt

        self.target_pose.pose.position.x += dx
        self.target_pose.pose.position.y += dy
        self.target_pose.pose.position.z += dz
        self.target_pose.pose.orientation.y += dyaw
        self.target_pose.pose.orientation.z += dpitch

        # Update timestamp
        self.target_pose.header.stamp = self.get_clock().now().to_msg()

        # Publish target
        self.target_pose_pub.publish(self.target_pose)

        # Gripper control
        gripper_msg = self._gripper_msg_type()

        if self._use_crisp_teleop:

            gripper_msg.data = float(self._crisp_gripper_msg_value)
            self.gripper_pub.publish(gripper_msg)
            return
       
        if self.gripper_close:
            gripper_msg.data = [self._gripper_close_value]  # Close gripper
            self.gripper_pub.publish(gripper_msg)
            self.gripper_close = False  # Reset the flag after sending the command 

        elif self.gripper_open:
            gripper_msg.data = [self._gripper_open_value]  # Open gripper
            self.gripper_pub.publish(gripper_msg)
            self.gripper_open = False  # Reset the flag after sending the command

def main(args=None):
    rclpy.init(args=args)

    node = PS5TeleopNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()