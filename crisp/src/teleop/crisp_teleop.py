import logging
import time
import numpy as np

from crisp_gym.teleop.teleop_sensor_stream import TeleopStreamedPose
from crisp_gym.util.setup_logger import setup_logging
from crisp_gym.envs.manipulator_env import ManipulatorCartesianEnv
from crisp_gym.envs.manipulator_env_config import make_env_config
from crisp_py.gripper.gripper import GripperConfig
from crisp_py.robot.robot_config import FrankaConfig, RobotConfig, make_robot_config

logger = logging.getLogger(__name__)
setup_logging()
teleop = TeleopStreamedPose()
#teleop.wait_until_ready()

env_config = make_env_config("franka_fm", control_frequency=100.0)
env = ManipulatorCartesianEnv(config=env_config)

# Initialize CRISP's target
env.robot.wait_until_ready()
env.robot.set_target(pose=teleop.last_pose)

previous_pose = teleop.last_pose

print("Environment created")
print("Target initialized")

if teleop.is_ready():
    print("Teleop is ready")
    while True:
        current_pose = teleop.last_pose
        action_pose = current_pose - previous_pose
        previous_pose = current_pose
        
        action = np.concatenate([
            action_pose.position,
            action_pose.orientation.as_euler("xyz"),
            [float(teleop.last_gripper)], 
        ])

        obs, *_ = env.step(action, block=True)

    