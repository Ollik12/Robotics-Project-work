from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

import os
import yaml

def launch_cameras(context):

    realsense_launch = os.path.join(
        get_package_share_directory("realsense2_camera"),
        "launch",
        "rs_launch.py",
    )
    
    wrist_serial = LaunchConfiguration("wrist_serial").perform(context)
    side_serial = LaunchConfiguration("side_serial").perform(context)

    wrist_color_profile = LaunchConfiguration("wrist_color_profile").perform(context)
    side_color_profile = LaunchConfiguration("side_color_profile").perform(context)

    # Create wrist_camera and side_camera GroupActions
    wrist_camera = GroupAction(
        scoped=True,
        forwarding=False,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(realsense_launch),
                launch_arguments={
                    "camera_namespace": "camera",
                    "camera_name": "wrist_camera",
                    "serial_no": wrist_serial,
                    "enable_color": "true",
                    "enable_depth": "false",
                    "rgb_camera.color_profile": wrist_color_profile,
                }.items(),
            ),
        ],
    )

    side_camera = GroupAction(
        scoped=True,
        forwarding=False,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(realsense_launch),
                launch_arguments={
                    "camera_namespace": "camera",
                    "camera_name": "side_camera",
                    "serial_no": side_serial,
                    "enable_color": "true",
                    "enable_depth": "false",
                    "rgb_camera.color_profile": side_color_profile,
                }.items(),
            ),
        ],
    )

    return [wrist_camera, side_camera]

def generate_launch_description():

    config_path = os.path.join(
        get_package_share_directory("franka_fm_cameras"),
        "config",
        "cameras.yaml",
    )

    with open(config_path, "r") as file:
        camera_config = yaml.safe_load(file)

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
            description="Color profile of the wrist camera",
        ),
        DeclareLaunchArgument(
            "side_color_profile",
            default_value=camera_config["side_camera"]["color_profile"],
            description="Color profile of the side camera",
        ),
        # Launch the cameras using OpaqueFunction to pass the context
        OpaqueFunction(function=launch_cameras),
    ])