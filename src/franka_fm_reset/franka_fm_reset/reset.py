import subprocess

from controller_manager_msgs.srv import SwitchController
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from std_srvs.srv import Trigger

"""
Reset Node
This node allows the user to reset the state of the robot/simulation.
"""

class ResetNode(Node):

    def __init__(self):
        super().__init__("reset_node")

        self.home_position = [
            0.0,
            -0.785,
            0.0,
            -2.356,
            0.0,
            1.571,
            0.785,
        ]

        self.joint_names = [
            "fr3_joint1",
            "fr3_joint2",
            "fr3_joint3",
            "fr3_joint4",
            "fr3_joint5",
            "fr3_joint6",
            "fr3_joint7",
        ]

        self.controller_switch_service = self.create_client(
            srv_type=SwitchController,
            srv_name="/controller_manager/switch_controller"
        )

        self.trajectory_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/joint_trajectory_controller/follow_joint_trajectory"
        )

        self.reset_teleop_client = self.create_client(
            Trigger,
            "/reset_teleop"
        )

        while not self.controller_switch_service.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Waiting for controller switch service...")

    def switch_controller(self, activate: str, deactivate: str):
        """
        Switches the active controller to the specified controller.
        """

        request = SwitchController.Request()

        request.activate_controllers = activate
        request.deactivate_controllers = deactivate

        self.get_logger().info(f"Switching to controller: {activate}")

        self.get_logger().info(f"Deactivating controller: {deactivate}")

        future = self.controller_switch_service.call_async(request)

        return future

    def home_robot(self):
        """
        Sends a trajectory to move the robot to the home position.
        """

        goal_msg = FollowJointTrajectory.Goal()

        goal_msg.trajectory.joint_names = self.joint_names

        point = JointTrajectoryPoint()
        point.positions = self.home_position
        point.time_from_start.sec = 5

        goal_msg.trajectory.points.append(point)

        self.get_logger().info("Sending trajectory to move to home position...")

        self.trajectory_client.wait_for_server()

        future = self.trajectory_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error("Home trajectory was rejected.")
            return False

        self.get_logger().info("Home trajectory accepted.")

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result().result

        if result.error_code != 0:
            self.get_logger().error(
                f"Home trajectory failed: {result.error_string}"
            )
            return False

        self.get_logger().info("Robot moved to home position.")
        return True

    def reset_cube(self):
        cmd = [
            "gz", "service",
            "-s", "/world/workcell/set_pose",
            "--reqtype", "gz.msgs.Pose",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "5000",
            "--req",
            "name: 'pick_place_box', "
            "position: {x: 0.1, y: 0.35, z: 1.02}, "
            "orientation: {x: 0, y: 0, z: 0, w: 1}"
        ]

        self.get_logger().info("Resetting cube position...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.get_logger().error(
                f"Failed to reset cube: {result.stderr}"
            )
            return False

        self.get_logger().info("Cube reset.")
        return True

    def reset_teleop(self):
        """
        Resets the teleop state.
        """
        self.get_logger().info("Resetting teleop state...")

        if not self.reset_teleop_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error("Reset teleop service not available.")
            return False

        request = Trigger.Request()

        future = self.reset_teleop_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()

        if response is None or not response.success:
            self.get_logger().error(
                f"Failed to reset teleop: {response.message if response else 'No response'}"
            )
            return False

        self.get_logger().info("Teleop state reset.")
        return True

    def reset_robot(self):

        self.get_logger().info("Starting robot reset...")

        if not self.switch_controller(
            activate=["joint_trajectory_controller"],
            deactivate=["cartesian_impedance_controller"],
        ):
            self.get_logger().error("Failed to switch to joint trajectory controller.")
            return False

        if not self.home_robot():
            self.get_logger().error("Failed to home robot.")
            return False

        if not self.switch_controller(
            activate=["cartesian_impedance_controller"],
            deactivate=["joint_trajectory_controller"],
        ):
            self.get_logger().error("Failed to switch back to Cartesian impedance.")
            return False

        if not self.reset_cube():
            self.get_logger().error("Failed to reset cube.")
            return False

        if not self.reset_teleop():
            self.get_logger().error("Failed to reset teleop state.")
            return False

        self.get_logger().info("Robot reset completed.")
        return True

def main(args=None):
    rclpy.init(args=args)

    node = ResetNode()


    node.reset_robot()

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()