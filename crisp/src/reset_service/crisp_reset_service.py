import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from crisp_gym.envs.manipulator_env import ManipulatorCartesianEnv

"""
Module for the CRISP reset service. 

This service allows for synchronizing the CRISP targets after a separate reset of the robot or simulation.
The service is implemented as a ROS2 node that provides a Trigger service. 
When the service is called, it will reset the targets of the robot in the ManipulatorCartesianEnv 
to synchronize with the current state of the robot or simulation.
"""


class CrispResetService(Node):
    def __init__(self, env: ManipulatorCartesianEnv):
        super().__init__("crisp_reset_service")

        self.env = env

        self.service = self.create_service(
            Trigger,
            "/crisp/reset_targets",
            self.reset_targets_callback,
        )

        self.get_logger().info("CRISP reset service ready")

    def reset_targets_callback(self, request, response):
        try:
            self.get_logger().info("Synchronizing CRISP targets")

            # Implement the appropriate synchronization here.
            self.env.robot.reset_targets()

            response.success = True
            response.message = "CRISP targets synchronized"

        except Exception as e:
            response.success = False
            response.message = str(e)

        return response