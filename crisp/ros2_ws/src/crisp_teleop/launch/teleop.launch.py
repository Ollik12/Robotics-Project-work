import os

from ament_index_python.packages import get_package_share_directory

from launch.actions import DeclareLaunchArgument
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    pkg_share = get_package_share_directory("crisp_teleop")

    default_config = os.path.join(
        pkg_share,
        "config",
        "teleop.yaml"
    )

    config_arg = DeclareLaunchArgument(
        "config",
        default_value=default_config,
        description="Teleop configuration file"
    )

    # Define the namespace argument for the robot
    # Default is empty, but can be set to "franka" when using with the real robot
    # Use: ros2 launch crisp_teleop teleop.launch.py namespace:=franka
    namespace_arg = DeclareLaunchArgument(
        "namespace",
        default_value="",
        description="Robot namespace"
    )

    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        output="screen",
    )

    teleop_node = Node(
        package="crisp_teleop",
        executable="teleop_node",
        name="crisp_teleop",
        output="screen",
        parameters=[LaunchConfiguration("config")],
    )

    return LaunchDescription([
        config_arg,
        namespace_arg,
        joy_node,
        teleop_node,
    ])