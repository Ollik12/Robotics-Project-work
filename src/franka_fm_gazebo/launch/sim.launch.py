# Copyright (c) 2024 Franka Robotics GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import xacro
import xml.dom.minidom

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit, OnShutdown

from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch import LaunchContext, LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def load_controller(context: LaunchContext, controller_name):
    controller_name_str = context.perform_substitution(controller_name)
    return [Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            controller_name_str,
            '--controller-manager-timeout', '30',
        ],
        parameters=[PathJoinSubstitution([
            FindPackageShare('franka_fm_gazebo'),
            'config',
            'controllers.yaml'
        ])],
        output='screen',
    )]


def get_robot_description(context: LaunchContext, robot_type, load_gripper, franka_hand):
    robot_type_str = context.perform_substitution(robot_type)
    load_gripper_str = context.perform_substitution(load_gripper)
    franka_hand_str = context.perform_substitution(franka_hand)

    franka_xacro_file = os.path.join(
        get_package_share_directory('franka_fm_gazebo'),
        'urdf', 'franka_arm.gazebo.xacro'
    )

    robot_description_config = xacro.process_file(
        franka_xacro_file,
        mappings={
            'robot_type': robot_type_str,
            'hand': load_gripper_str,
            'gazebo': 'true',
            'ee_id': franka_hand_str,
            'gazebo_effort': 'true',
        }
    )

    if not isinstance(robot_description_config, xml.dom.minidom.Document):
        raise RuntimeError(
            f'The given xacro file {franka_xacro_file} is not a valid xml format.')

    robot_description = {'robot_description': robot_description_config.toxml()}

    return [Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[robot_description],
    )]


def generate_launch_description():
    # Configure ROS nodes for launch
    load_gripper_name = 'load_gripper'
    franka_hand_name = 'franka_hand'
    robot_type_name = 'robot_type'
    namespace_name = 'namespace'
    controller_name = 'controller'
    rviz_name = 'rviz'
    gz_args_name = 'gz_args'

    load_gripper = LaunchConfiguration(load_gripper_name)
    franka_hand = LaunchConfiguration(franka_hand_name)
    robot_type = LaunchConfiguration(robot_type_name)
    namespace = LaunchConfiguration(namespace_name)
    controller = LaunchConfiguration(controller_name)
    rviz = LaunchConfiguration(rviz_name)
    gz_args = LaunchConfiguration(gz_args_name)

    load_gripper_launch_argument = DeclareLaunchArgument(
        load_gripper_name,
        default_value='true',
        description='true/false for activating the gripper')
    franka_hand_launch_argument = DeclareLaunchArgument(
        franka_hand_name,
        default_value='franka_hand',
        description='Default value: franka_hand')
    robot_type_launch_argument = DeclareLaunchArgument(
        robot_type_name,
        default_value='fr3',
        description='Available values: fr3, fp3 and fer')
    namespace_launch_argument = DeclareLaunchArgument(
        namespace_name,
        default_value='',
        description='Namespace for the robot. If not set, the robot will be launched in the root namespace.')
    controller_launch_argument = DeclareLaunchArgument(
        controller_name,
        default_value='cartesian_impedance_controller',
        description='The controller name to be used. You can choose one from the controllers.yaml.')
    gz_args_launch_argument = DeclareLaunchArgument(
        gz_args_name,
        default_value='empty.sdf -r',
        description='Extra args to be forwared to gazebo')
    rviz_launch_argument = DeclareLaunchArgument(
        rviz_name,
        default_value='true',
        description='true/false for visualizing the robot in rviz')

    # Get robot description
    robot_state_publisher = OpaqueFunction(
        function=get_robot_description,
        args=[robot_type, load_gripper, franka_hand])

    # Gazebo Sim
    fm_robo_pkg = get_package_share_directory('franka_fm_gazebo')
    world_file = os.path.join(fm_robo_pkg, 'worlds', 'workcell.sdf')

    gazebo_gui_config = os.path.join(fm_robo_pkg, 'config', 'gui.config')
    gz_args = f'{world_file} -r --gui-config {gazebo_gui_config}'

    # Gazebo Sim resource path (needed for loading meshes and sdf files)
    os.environ['GZ_SIM_RESOURCE_PATH'] = os.pathsep.join([
        fm_robo_pkg,
        os.path.dirname(get_package_share_directory('franka_description')),
    ])

    gazebo_launch = IncludeLaunchDescription(
        PathJoinSubstitution([
            FindPackageShare('ros_gz_sim'),
            'launch',
            'gz_sim.launch.py'
        ]),
        launch_arguments={'gz_args': gz_args}.items(),
    )

    spawn = Node(
        package='ros_gz_sim', executable='create',
        arguments=['-topic', '/robot_description',
                   '-x', '-0.35',
                   '-y', '0.0',
                   '-z', '1.0',],
        output='screen',
    )

    rviz_file = os.path.join(get_package_share_directory('franka_description'),
                             'rviz', 'visualize_franka.rviz')

    rviz_node = Node(package='rviz2',
                     executable='rviz2',
                     name='rviz2',
                     namespace=namespace,
                     arguments=['--display-config', rviz_file, '-f', 'world'],
                     condition=IfCondition(rviz))

    launch_controller = OpaqueFunction(
        function=load_controller,
        args=[controller]
    )

    controllers = PathJoinSubstitution([
        FindPackageShare('franka_fm_gazebo'),
        'config',
        'controllers.yaml'
    ])

    # Launch joy_node for joystick control
    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        output="screen",
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )

    wrist_camera_bridge = Node(
        package="ros_gz_image",
        executable="image_bridge",
        arguments=['/wrist_camera/image'],
        output="screen",
    )

    return LaunchDescription([
        load_gripper_launch_argument,
        franka_hand_launch_argument,
        robot_type_launch_argument,
        namespace_launch_argument,
        gz_args_launch_argument,
        rviz_launch_argument,
        clock_bridge,
        wrist_camera_bridge,
        gazebo_launch,
        robot_state_publisher,
        rviz_node,
        spawn,
        joy_node,

        Node(
            package='controller_manager',
            executable='spawner',
            arguments=[
                'joint_state_broadcaster',
            ],
            parameters=[controllers],
            output='screen',
        ),

        # Activate cartesion_impedance_controller
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["cartesian_impedance_controller"],
            parameters=[controllers],
            output="screen",
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["joint_impedance_controller", "--inactive"],
            parameters=[controllers],
            output="screen",
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["joint_trajectory_controller", "--inactive"],
            parameters=[controllers],
            output="screen",
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["gravity_compensation", "--inactive"],
            parameters=[controllers],
            output="screen",
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["pose_broadcaster"],
            parameters=[controllers],
            output="screen",
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["twist_broadcaster"],
            parameters=[controllers],
            output="screen",
        ),

        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["gripper_controller"],
            parameters=[controllers],
            output="screen",
        ),

        RegisterEventHandler(
            OnShutdown(
                on_shutdown=[
                    ExecuteProcess(
                        cmd=['pkill', '-SIGINT', 'ruby'],
                        name='gz_sim_graceful_shutdown',
                    )
                ]
            )
        )
    ])