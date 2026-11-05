import rclpy
from rclpy.node import Node

import numpy as np

from sensor_msgs.msg import Image, JointState
from cv_bridge import CvBridge
from std_msgs.msg import Float32MultiArray

from openpi_client import websocket_client_policy
from geometry_msgs.msg import PoseStamped
from scipy.spatial.transform import Rotation


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

        self.action_pub = self.create_publisher(
            Float32MultiArray,
            "/pi05/actions",
            10,
        )

        # Run inference periodically.
        self.timer = self.create_timer(
            0.5,
            self.inference_callback,
        )

        self.prompt = "pick up the object"

        self.current_pose = None

        self.create_subscription(
            PoseStamped, "/current_pose", self.current_pose_callback, 10
        )

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
            dtype=np.float32,
        )
        
        self.gripper_position = np.asarray(
            [msg.position[0]],
            dtype=np.float32,
        )

    def inference_callback(self):
        if (
            self.side_image is None
            or self.wrist_image is None
            #or self.joint_position is None
            or self.gripper_position is None
            or self.current_pose is None
        ):
            return

        observation = {
            "observation/image": self.side_image,
            "observation/wrist_image": self.wrist_image,
            "observation/state": np.concatenate([
                self.current_pose,
                self.gripper_position,
            ]),
            "prompt": self.prompt,
        }



        self.get_logger().info(
            "Sending observation to OpenPI..."
        )

        try:
            result = self.policy.infer(observation)
            actions = np.asarray(result["actions"], dtype=np.float32)

            self.get_logger().info(
                f"Received action chunk: {actions.shape}"
            )
            #self.get_logger().info(f"Action chunk:\n{actions}")

            msg = Float32MultiArray()
            msg.data = actions.flatten().tolist()
            self.action_pub.publish(msg)

        except Exception as e:
            self.get_logger().error(
                f"OpenPI inference failed: {e}"
            )

    def pose_to_xyz_rpy(self, msg):
        p = msg.pose.position
        q = msg.pose.orientation

        rpy = Rotation.from_quat([q.x, q.y, q.z, q.w]).as_euler("xyz")

        return np.array(
            [p.x, p.y, p.z, rpy[0], rpy[1], rpy[2]],
            dtype=np.float32,
        )

    def current_pose_callback(self, msg):
        self.current_pose = self.pose_to_xyz_rpy(msg)


def main(args=None):
    rclpy.init(args=args)

    node = OpenPiInference()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.policy._ws.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()