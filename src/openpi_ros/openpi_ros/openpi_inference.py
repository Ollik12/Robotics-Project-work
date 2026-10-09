import rclpy
from rclpy.node import Node

import numpy as np

from sensor_msgs.msg import Image, JointState
from cv_bridge import CvBridge

from openpi_client import websocket_client_policy


class OpenPiInference(Node):
    def __init__(self):
        super().__init__("openpi_inference")

        # OpenPI server
        self.policy = websocket_client_policy.WebsocketClientPolicy(
            host="127.0.0.1",
            port=8000,
        )

        self.get_logger().info("Connected to OpenPI server.")

        self.bridge = CvBridge()

        # Latest observations
        self.side_image = None
        self.wrist_image = None
        self.joint_position = None
        self.gripper_position = None

        self.create_subscription(
            Image,
            "/side_camera/image",
            self.side_camera_callback,
            10,
        )

        self.create_subscription(
            Image,
            "/wrist_camera/image",
            self.wrist_camera_callback,
            10,
        )

        self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_state_callback,
            10,
        )

        # Run inference periodically.
        self.timer = self.create_timer(
            1.0,
            self.inference_callback,
        )

        self.prompt = "pick up the object"

    def side_camera_callback(self, msg):
        self.side_image = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding="rgb8",
        )

    def wrist_camera_callback(self, msg):
        self.wrist_image = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding="rgb8",
        )

    def joint_state_callback(self, msg):
        self.joint_position = np.asarray(
            msg.position[2:9],
            dtype=np.float64,
        )
        
        self.gripper_position = np.asarray(
            [msg.position[0]],
            dtype=np.float64,
        )

    def inference_callback(self):
        # Don't run until all observations exist.
        if self.side_image is None:
            self.get_logger().info(
                "Waiting for side camera..."
            )
            return

        if self.wrist_image is None:
            self.get_logger().info(
                "Waiting for wrist camera..."
            )
            return

        if self.joint_position is None:
            self.get_logger().info(
                "Waiting for joint state..."
            )
            return

        if self.gripper_position is None:
            self.get_logger().info(
                "Waiting for gripper state..."
            )
            return

        observation = {
            "observation/image": self.side_image,
            "observation/wrist_image": self.wrist_image,
            "observation/state": np.concatenate([
                self.joint_position,
                self.gripper_position,
            ]),
            "prompt": self.prompt,
        }

        self.get_logger().info(
            "Sending observation to OpenPI..."
        )

        try:
            result = self.policy.infer(observation)

            actions = result["actions"]

            self.get_logger().info(
                f"Received action chunk: {actions.shape}"
            )

        except Exception as e:
            self.get_logger().error(
                f"OpenPI inference failed: {e}"
            )


def main(args=None):
    rclpy.init(args=args)

    node = OpenPiInference()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()