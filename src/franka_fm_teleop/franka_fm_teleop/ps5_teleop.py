import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Joy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float64MultiArray


class PS5TeleopNode(Node):

    def __init__(self):
        super().__init__("ps5_teleop_node")

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

        # Subscribers
        self.joy_sub = self.create_subscription(
            Joy,
            "/joy",
            self.joy_callback,
            10,
        )

        self.ee_pose_sub = self.create_subscription(
            PoseStamped,
            "/current_pose",
            self.ee_pose_callback,
            10,
        )

        # Pose publisher
        self.target_pose_pub = self.create_publisher(
            PoseStamped,
            "/target_pose",
            10,
        )

        # Gripper control publisher
        self.gripper_pub = self.create_publisher(
            Float64MultiArray,
            "/gripper_controller/commands",
            10,
        )

        # 100 Hz update timer
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
        
        # X
        self.gripper_close = bool(msg.buttons[0])
        # O
        self.gripper_open = bool(msg.buttons[1])

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

        if not self.enabled:
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
        gripper_msg = Float64MultiArray()
        if self.gripper_close:
            gripper_msg.data = [-2.5]  # Close gripper
        elif self.gripper_open:
            gripper_msg.data = [0.05]  # Open gripper

        # Publish gripper command
        if self.gripper_close or self.gripper_open:
            self.gripper_pub.publish(gripper_msg)

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