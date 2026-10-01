import os
import signal
import subprocess
import sys
import termios
import threading
import tty
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

"""
Bag Recorder Node
This node allows the user to record ROS2 bag files for specific topics.
"""

class BagRecorder(Node):

    BAG_OUTPUT_DIR = "/ros2_ws/src/franka_fm_rec/bags"

    TOPICS = [
        "/wrist_camera/image",
        "/joint_states",
        "/target_pose",
        "/task",
        "/gripper_controller/commands",
    ]

    TASK = "Test data collection"

    def __init__(self):
        super().__init__("bag_recorder")

        os.makedirs(self.BAG_OUTPUT_DIR, exist_ok=True)

        self.recording_process = None
        self.episode_number = 0

        self.task_publisher = self.create_publisher(
            String,
            "/task",
            10
        )

        self.task_timer = self.create_timer(
            1.0,
            self.publish_task
        )

        self.get_logger().info("================================")
        self.get_logger().info("      Franka Bag Recorder")
        self.get_logger().info("================================")
        self.get_logger().info("[r] Start recording")
        self.get_logger().info("[s] Stop recording")
        self.get_logger().info("[q] Quit")
        self.get_logger().info("================================")

        self.keyboard_thread = threading.Thread(
            target=self.keyboard_loop,
            daemon=True
        )
        self.keyboard_thread.start()

    def keyboard_loop(self):
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            tty.setcbreak(sys.stdin.fileno())

            while rclpy.ok():
                key = sys.stdin.read(1).lower()

                if key == "r":
                    self.start_recording()

                elif key == "s":
                    self.stop_recording()

                elif key == "q":
                    self.stop_recording()
                    rclpy.shutdown()
                    break

        finally:
            termios.tcsetattr(
                sys.stdin,
                termios.TCSADRAIN,
                old_settings
            )

    def start_recording(self):
        if self.recording_process is not None:
            self.get_logger().warn("Already recording.")
            return

        self.episode_number += 1

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        bag_path = os.path.join(
            self.BAG_OUTPUT_DIR,
            f"episode_{self.episode_number}_{timestamp}"
        )

        command = [
            "ros2",
            "bag",
            "record",
            "-o",
            bag_path,
            *self.TOPICS,
        ]

        self.get_logger().info(
            f"Starting episode {self.episode_number}"
        )

        try:
            self.recording_process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
            )

        except Exception as e:
            self.recording_process = None
            self.get_logger().error(
                f"Failed to start recording: {e}"
            )
            return

        self.get_logger().info("RECORDING")

    def stop_recording(self):
        if self.recording_process is None:
            self.get_logger().warn("Not currently recording.")
            return

        self.get_logger().info("Stopping recording...")

        self.recording_process.send_signal(signal.SIGINT)
        self.recording_process.wait()

        self.recording_process = None

        self.get_logger().info("Recording stopped.")

    def publish_task(self):
        if self.recording_process is None:
            return

        msg = String()
        msg.data = self.TASK
        self.task_publisher.publish(msg)

    def destroy_node(self):
        self.stop_recording()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    node = BagRecorder()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()