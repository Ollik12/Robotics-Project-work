"""Script showcasing how to record data in Lerobot Format."""

import argparse
import json
import logging


import numpy as np
import rclpy

import crisp_gym  # noqa: F401
from crisp_gym.config.home import HomeConfig
from crisp_gym.envs.manipulator_env_config import make_env_config
from crisp_gym.envs.manipulator_env import ManipulatorCartesianEnv, make_env
from crisp_gym.envs.manipulator_env_config import list_env_configs
from crisp_gym.record.record_functions import make_teleop_fn, make_teleop_streamer_fn
from crisp_gym.record.recording_manager import make_recording_manager
from crisp_gym.teleop.teleop_robot import TeleopRobot, make_leader
from crisp_gym.teleop.teleop_robot_config import list_leader_configs
from crisp_gym.teleop.teleop_sensor_stream import TeleopStreamedPose
from crisp_gym.util import prompt
from crisp_gym.util.lerobot_features import get_features
from crisp_gym.util.setup_logger import setup_logging

ROBOT_HOME_POS = [0.31, 0.0, 0.486]

def main():
    """Record data in Lerobot Format using a leader-follower teleoperation setup."""
    parser = argparse.ArgumentParser(description="Record data in Lerobot Format")
    parser.add_argument(
        "--repo-id",
        type=str,
        default="test",
        help="Repository ID for the dataset",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        nargs="+",
        default=["pick the lego block."],
        help="List of task descriptions to record data for, e.g. 'clean red' 'clean green'",
    )
    parser.add_argument(
        "--robot-type",
        type=str,
        default="franka",
        help="Type of robot being used.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=15,
        help="Frames per second for recording",
    )
    parser.add_argument(
        "--num-episodes",
        type=int,
        default=100,
        help="Number of episodes to record",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume recording of an already existing dataset",
    )
    parser.add_argument(
        "--push-to-hub",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether to push the dataset to the Hugging Face Hub.",
    )
    parser.add_argument(
        "--recording-manager-type",
        type=str,
        default="keyboard",
        help="Type of recording manager to use. Currently only 'keyboard' and 'ros' are supported.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logger level.",
    )
    parser.add_argument(
        "--home-config-noise",
        type=float,
        default=0.0,
        help="Noise to add to the home configuration when homing the robots to randomize the position a bit.",
    )

    args = parser.parse_args()

    # Set up logger
    logger = logging.getLogger(__name__)
    setup_logging(level=args.log_level)

    logger.info("Arguments:")
    for arg, value in vars(args).items():
        logger.info(f"{arg:<30}: {value}")

    env_config = env_config = make_env_config("franka_fm")

    try:

        env = ManipulatorCartesianEnv(config=env_config)

        leader = TeleopStreamedPose()
        logger.info("Using streamed teleop for the leader robot.")

        keys_to_ignore = []
        features = get_features(env=env, ignore_keys=keys_to_ignore)
        logger.debug(f"Using the features: {features}")

        env.robot.wait_until_ready()

        if leader.is_ready():
            env.robot.set_target(pose=leader.last_pose)

        recording_manager = make_recording_manager(
            recording_manager_type=args.recording_manager_type,
            features=features,
            repo_id=args.repo_id,
            robot_type=args.robot_type,
            num_episodes=args.num_episodes,
            fps=args.fps,
            resume=args.resume,
            push_to_hub=args.push_to_hub,
        )
        recording_manager.wait_until_ready()
        logger.info("Recording manager is ready.")

        env_metadata = env.get_metadata()

        with open(recording_manager.dataset_directory / "meta" / "crisp_meta.json", "w") as f:
            json.dump(env_metadata, f, indent=4)

        logger.info(
            f"Environment metadata saved to {recording_manager.dataset_directory / 'meta' / 'crisp_meta.json'}"
        )
        tasks = list(args.tasks)

        def on_start():
            """Hook function to be called when starting a new episode."""
            env.robot.reset_targets()
            

        def on_end():
            """Hook function to be called when stopping the recording."""

            env.robot.reset_targets()
            env.gripper.open()
            env.robot.wait_until_ready()

            # TEMPORARY FIX!
            # Robot teleop is reset with franka_fm_reset, but this ensures that the CRISP side
            # also has the same target pose. 
            # Will be removed once the reset is handled in a more robust way.
            env.robot.set_target(position=ROBOT_HOME_POS)

        with recording_manager:
            while not recording_manager.done():
                logger.info(
                    f"→ Episode {recording_manager.episode_count + 1} / {recording_manager.num_episodes}"
                )

                # Create a new teleop function for each episode to reset internal variables
                teleop_fn = None
                if isinstance(leader, TeleopStreamedPose) and isinstance(
                    env, ManipulatorCartesianEnv
                ):
                    teleop_fn = make_teleop_streamer_fn(env, leader)
                else:
                    raise ValueError(
                        "Streamed teleop is only compatible with Cartesian control. Please disable joint control."
                    )

                task = tasks[np.random.randint(0, len(tasks))] if tasks else "No task specified."
                logger.info(f"▷ Task: {task}")

                recording_manager.record_episode(
                    data_fn=teleop_fn,
                    task=task,
                    on_start=on_start,
                    on_end=on_end,
                )

        logger.info("Closing the environment.")
        env.close()

        logger.info("Finished recording.")

    except TimeoutError as e:
        logger.exception(f"Timeout error occurred during recording: {e}.")
        logger.error(
            "Please check if the robot container is running and the namespace is correct."
            "\nYou can check the topics using `ros2 topic list` command."
        )

    except Exception as e:
        logger.exception(f"An error occurred during recording: {e}.")

    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
