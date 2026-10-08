import sys
import select
import termios
import tty
import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float64MultiArray, Float32
from rclpy.qos import qos_profile_sensor_data
from std_srvs.srv import Trigger


class KeyboardTeleopNode(Node):

    def __init__(self):
        super().__init__("keyboard_teleop_node")

        self._use_crisp_teleop = False

        if '--crisp-teleop' in sys.argv:
            # Publish for CRISP teleop
            self._gripper_topic = "/phone_gripper"
            self._target_pose_topic = "/phone_pose"
            self._gripper_open_value = 1.0
            self._gripper_close_value = 0.0
            self._use_crisp_teleop = True

            # Initially 0 = close
            self._crisp_gripper_msg_value = 0.0
            self._gripper_msg_type = Float32

        else:
            # Publish straight to the robot for Franka teleop
            self._gripper_topic = "/gripper_position_controller/commands"
            self._target_pose_topic = "/target_pose"
            self._gripper_open_value = 0.035
            self._gripper_close_value = 0.0
            self._gripper_msg_type = Float64MultiArray

        # Parameters
        self.speed = 0.10          # m/s
        self.update_rate = 100.0   # Hz

        # How long a movement key stays active
        # after the last keyboard event.
        self.key_timeout = 0.15

        # Smooth acceleration
        self.acceleration = 0.5    # m/s^2

        # Keyboard state
        self.enabled = False

        self.key_times = {
            "w": 0.0,
            "s": 0.0,
            "a": 0.0,
            "d": 0.0,
            "r": 0.0,
            "f": 0.0,
        }

        # Current Cartesian velocity
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.velocity_z = 0.0

        # Gripper state
        self.gripper_close = False
        self.gripper_open = False

        # Target pose
        self.target_pose = None

        # Current robot pose
        self.ee_pose_sub = self.create_subscription(
            PoseStamped,
            "/current_pose",
            self.ee_pose_callback,
            qos_profile=qos_profile_sensor_data,
        )

        # Target pose
        self.target_pose_pub = self.create_publisher(
            PoseStamped,
            self._target_pose_topic,
            10,
        )

        # Gripper
        self.gripper_pub = self.create_publisher(
            self._gripper_msg_type,
            self._gripper_topic,
            qos_profile=qos_profile_sensor_data,
        )

        # Reset service to sync teleop pose after robot reset
        self.reset_service = self.create_service(
            Trigger,
            "/reset_teleop",
            self.reset_teleop,
        )

        # Save terminal settings
        self.terminal_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

        # 100 Hz update timer
        self.timer = self.create_timer(
            1.0 / self.update_rate,
            self.update,
        )

        self.get_logger().info(
            "Keyboard teleop node started."
        )

        print("")
        print("======================================")
        print("        FR3 Keyboard Teleoperation")
        print("======================================")
        print("")
        print("Movement:")
        print("  W / S       X forward / backward")
        print("  A / D       Y left / right")
        print("  R / F       Z up / down")
        print("")
        print("  Hold keys for continuous movement")
        print("  W + A/D     Diagonal movement")
        print("")
        print("  SPACE       Enable / disable")
        print("")
        print("Gripper:")
        print("  O           Open")
        print("  P           Close")
        print("")
        print("  Q           Quit")
        print("")
        print("Press SPACE to enable teleoperation.")
        print("======================================")
        print("")

    def reset_teleop(self, request, response):
        """Reset the teleoperation state."""

        if self.target_pose is not None:
            # Keep the current robot pose as the target pose
            # so teleoperation remains synchronized.
            self.target_pose = PoseStamped()
            self.target_pose.header = self.target_pose.header
            self.target_pose.pose = self.target_pose.pose

        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.velocity_z = 0.0

        response.success = True
        response.message = "Teleop state reset"

        return response

    def ee_pose_callback(self, msg):
        """Initialize target pose from current robot pose."""

        if self.target_pose is None:

            self.target_pose = PoseStamped()

            self.target_pose.header = msg.header
            self.target_pose.pose = msg.pose

            self.get_logger().info(
                "Initial target pose received."
            )

    def get_key(self):
        """Read one keyboard character without blocking."""

        if select.select(
            [sys.stdin],
            [],
            [],
            0.0
        )[0]:

            return sys.stdin.read(1)

        return None

    def process_key(self, key):
        """Process keyboard input."""

        now = time.monotonic()

        # Enable / disable
        if key == " ":

            self.enabled = not self.enabled

            if self.enabled:

                self.get_logger().info(
                    "Teleoperation ENABLED"
                )

            else:

                self.get_logger().info(
                    "Teleoperation DISABLED"
                )

                # Stop immediately
                self.velocity_x = 0.0
                self.velocity_y = 0.0
                self.velocity_z = 0.0

            return

        # Quit
        if key == "q":
            raise KeyboardInterrupt

        # Movement keys
        if key in self.key_times:

            self.key_times[key] = now

        # Gripper
        elif key == "o":
            # if we want to use crisp teleop
            if self._use_crisp_teleop:
                # CRISP: open = 1.0
                self._crisp_gripper_msg_value = (
                    self._gripper_open_value
                )

            else:
                self.gripper_open = True
                self.gripper_close = False

        elif key == "p":

            if self._use_crisp_teleop:
                # CRISP: close = 0.0
                self._crisp_gripper_msg_value = (
                    self._gripper_close_value
                )

            else:
                self.gripper_close = True
                self.gripper_open = False

    def key_active(self, key, now):
        """Check whether a movement key is still active."""

        return (
            now - self.key_times[key]
            < self.key_timeout
        )

    def move_towards(
        self,
        current,
        target,
        max_change
    ):
        """Smoothly move current velocity toward target."""

        difference = target - current

        if abs(difference) <= max_change:
            return target

        if difference > 0:
            return current + max_change

        return current - max_change

    def update(self):

        # Read all available keyboard input
        while True:

            key = self.get_key()

            if key is None:
                break

            self.process_key(key)

        # No robot pose yet
        if self.target_pose is None:
            return

        # ==========================================================
        # CRISP TELEOP
        # ==========================================================
        #
        # CRISP expects the pose and gripper state to be streamed
        # continuously, even when the keyboard teleoperation is
        # disabled.
        #
        if self._use_crisp_teleop and not self.enabled:

            # Update timestamp
            self.target_pose.header.stamp = (
                self.get_clock().now().to_msg()
            )

            # Publish pose
            self.target_pose_pub.publish(
                self.target_pose
            )

            # Publish gripper state
            gripper_msg = Float32()

            gripper_msg.data = float(
                self._crisp_gripper_msg_value
            )

            self.gripper_pub.publish(
                gripper_msg
            )

            return

        # ==========================================================
        # NORMAL FRANKA TELEOP
        # ==========================================================

        # Teleoperation disabled
        if not self.enabled:

            self.velocity_x = 0.0
            self.velocity_y = 0.0
            self.velocity_z = 0.0

            return

        now = time.monotonic()

        # Requested movement
        x_input = 0.0
        y_input = 0.0
        z_input = 0.0

        if self.key_active("w", now):
            x_input += 1.0

        if self.key_active("s", now):
            x_input -= 1.0

        if self.key_active("a", now):
            y_input += 1.0

        if self.key_active("d", now):
            y_input -= 1.0

        if self.key_active("r", now):
            z_input += 1.0

        if self.key_active("f", now):
            z_input -= 1.0

        # Normalize diagonal movement
        magnitude = (
            x_input ** 2
            + y_input ** 2
            + z_input ** 2
        ) ** 0.5

        if magnitude > 1.0:

            x_input /= magnitude
            y_input /= magnitude
            z_input /= magnitude

        # Desired velocity
        target_vx = x_input * self.speed
        target_vy = y_input * self.speed
        target_vz = z_input * self.speed

        # Time step
        dt = 1.0 / self.update_rate

        # Maximum velocity change this cycle
        max_change = self.acceleration * dt

        # Smooth acceleration/deceleration
        self.velocity_x = self.move_towards(
            self.velocity_x,
            target_vx,
            max_change,
        )

        self.velocity_y = self.move_towards(
            self.velocity_y,
            target_vy,
            max_change,
        )

        self.velocity_z = self.move_towards(
            self.velocity_z,
            target_vz,
            max_change,
        )

        # Position increment
        dx = self.velocity_x * dt
        dy = self.velocity_y * dt
        dz = self.velocity_z * dt

        self.target_pose.pose.position.x += dx
        self.target_pose.pose.position.y += dy
        self.target_pose.pose.position.z += dz

        # Timestamp
        self.target_pose.header.stamp = (
            self.get_clock().now().to_msg()
        )

        # Publish target pose
        self.target_pose_pub.publish(
            self.target_pose
        )

        # ==========================================================
        # GRIPPER
        # ==========================================================

        if self._use_crisp_teleop:

            # CRISP gripper state is continuously published.
            gripper_msg = Float32()

            gripper_msg.data = float(
                self._crisp_gripper_msg_value
            )

            self.gripper_pub.publish(
                gripper_msg
            )

            return

        # Normal Franka gripper:
        # only publish when O/P was pressed.
        if self.gripper_close or self.gripper_open:

            gripper_msg = Float64MultiArray()

            if self.gripper_close:

                gripper_msg.data = [
                    self._gripper_close_value
                ]

            elif self.gripper_open:

                gripper_msg.data = [
                    self._gripper_open_value
                ]

            self.gripper_pub.publish(
                gripper_msg
            )

            # Only send once
            self.gripper_close = False
            self.gripper_open = False

    def shutdown(self):
        """Restore terminal settings."""

        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            self.terminal_settings,
        )


def main(args=None):

    rclpy.init(args=args)

    node = KeyboardTeleopNode()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:

        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()