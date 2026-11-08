from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

import os
import yaml


def generate_launch_description():

    realsense_launch = os.path.join(
        get_package_share_directory("realsense2_camera"),
        "launch",
        "rs_launch.py",
    )

    config_path = os.path.join(
        get_package_share_directory("franka_fm_cameras"),
        "config",
        "cameras.yaml",
    )

    with open(config_path, "r") as file:
        camera_config = yaml.safe_load(file)

    wrist_serial = LaunchConfiguration("wrist_serial")
    side_serial = LaunchConfiguration("side_serial")

    wrist_camera = GroupAction(
        scoped=True,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(realsense_launch),
                launch_arguments={
                    "camera_namespace": "wrist_camera",
                    "camera_name": "camera",
                    "serial_no": LaunchConfiguration("wrist_serial"),
                    "enable_color": "true",
                    "enable_depth": "false",
                    "rgb_camera.color_profile": LaunchConfiguration("wrist_color_profile"),
                }.items(),
            ),
        ],
    )

    side_camera = GroupAction(
        scoped=True,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(realsense_launch),
                launch_arguments={
                    "camera_namespace": "side_camera",
                    "camera_name": "camera",
                    "serial_no": LaunchConfiguration("side_serial"),
                    "enable_color": "true",
                    "enable_depth": "false",
                    "rgb_camera.color_profile": LaunchConfiguration("side_color_profile"),
                }.items(),
            ),
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "wrist_serial",
            default_value=camera_config["wrist_camera"]["serial_no"],
            description="Serial number of the wrist camera",
        ),
        DeclareLaunchArgument(
            "side_serial",
            default_value=camera_config["side_camera"]["serial_no"],
            description="Serial number of the side camera",
        ),
        DeclareLaunchArgument(
            "wrist_color_profile",
            default_value=camera_config["wrist_camera"]["color_profile"],
        ),
        DeclareLaunchArgument(
            "side_color_profile",
            default_value=camera_config["side_camera"]["color_profile"],
        ),
        wrist_camera,
        side_camera,
    ])