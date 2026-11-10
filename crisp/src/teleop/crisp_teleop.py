import logging
import time
import numpy as np
import rclpy
from rclpy.signals import SignalHandlerOptions

from crisp_gym.teleop.teleop_sensor_stream import TeleopStreamedPose
from crisp_gym.util.setup_logger import setup_logging
from crisp_gym.envs.manipulator_env import ManipulatorCartesianEnv
from crisp_gym.envs.manipulator_env_config import make_env_config

logger = logging.getLogger(__name__)
setup_logging()
rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
teleop = TeleopStreamedPose()

env_config = make_env_config("franka_fm_sim", control_frequency=30.0)
env = ManipulatorCartesianEnv(config=env_config)

# Initialize CRISP's target
env.robot.wait_until_ready()
env.robot.set_target(pose=teleop.last_pose)

previous_pose = teleop.last_pose

print("Environment created")
print("Target initialized")

env.wait_until_ready()

if teleop.is_ready():
    print("Teleop is ready")

    try:
        while True:
            env.robot.controller_switcher_client.switch_controller(controller_name="cartesian_impedance_controller")
            current_pose = teleop.last_pose
            action_pose = current_pose - previous_pose
            previous_pose = current_pose

            action = np.concatenate([
                action_pose.position,
                action_pose.orientation.as_euler("xyz"),
                [float(teleop.last_gripper)],
            ])

            obs, *_ = env.step(action, block=True)
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        print("Homing robot...")
        try:
            env.robot.home(blocking=True)
            print("Robot homed")
        finally:
            if rclpy.ok():
                rclpy.shutdown()