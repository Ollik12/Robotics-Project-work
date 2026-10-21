import numpy as np
import rclpy

from rclpy.node import Node
from std_msgs.msg import Float32MultiArray

from crisp_gym.util.setup_logger import setup_logging
from crisp_gym.envs.manipulator_env import ManipulatorCartesianEnv
from crisp_gym.envs.manipulator_env_config import make_env_config


class Pi05Controller(Node):
    def __init__(self):
        super().__init__("pi05_controller")

        self.action_chunk = None
        self.create_subscription(
            Float32MultiArray,
            "/pi05/actions",
            self.action_callback,
            10,
        )
        self.control_frequency = 20.0
        self.create_timer(1.0 / self.control_frequency, self.execute_action_chunk)
        setup_logging()

        env_config = make_env_config(
            "franka_fm",
            control_frequency=self.control_frequency,
            use_relative_actions=True,
        )
        self.env = ManipulatorCartesianEnv(config=env_config)
        self.env.robot.wait_until_ready()
        #self.env.wait_until_ready()
        self.get_logger().info("CRISP environment ready.")


    def action_callback(self, msg):
        actions = np.asarray(msg.data, dtype=np.float32) # Shape: (7 * action_horizon)

        if actions.size % 7 != 0:
            self.get_logger().error(
                f"Invalid action size: {actions.size}"
            )
            return

        self.action_chunk = actions.reshape(-1, 7) # Shape: (action_horizon, 7)


    def execute_action_chunk(self):
        if self.action_chunk is None:
            return

        actions = self.action_chunk
        self.action_chunk = None

        for action in actions:
            delta_pose = action[:6]
            gripper = float(action[6])

            crisp_action = np.concatenate([
                delta_pose,
                [gripper],
            ])

            self.env.step(crisp_action, block=True)



def main(args=None):
    rclpy.init(args=args)
    node = Pi05Controller()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()