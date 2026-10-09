# Start with an official ROS 2 base image for the desired distribution
FROM ros:jazzy-ros-base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    ROS_DISTRO=jazzy \
    RCUTILS_COLORIZED_OUTPUT=1

ARG USERNAME=developer

# Install essential packages and ROS development tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash-completion \
        curl \
        gdb \
        git \
        nano \
        iputils-ping \
        openssh-client \
        python3-pip \
        python3-colcon-argcomplete \
        python3-colcon-common-extensions \
        sudo \
        vim \
        libgtest-dev \
        libgmock-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Setup user configuration
RUN usermod --login $USERNAME ubuntu \
    && groupmod --new-name $USERNAME ubuntu \
    && usermod --home /home/$USERNAME --move-home $USERNAME

RUN apt-get update \
    && apt-get install -y sudo \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

USER $USERNAME

# Install some ROS 2 dependencies to create a cache layer
RUN sudo apt-get update \
    && sudo apt-get install -y --no-install-recommends \
        ros-jazzy-gz-sim-vendor \
        ros-jazzy-gz-plugin-vendor \
        ros-jazzy-sdformat-urdf \
        ros-jazzy-joint-state-publisher-gui \
        ros-jazzy-ros2controlcli \
        ros-jazzy-controller-interface \
        ros-jazzy-hardware-interface-testing \
        ros-jazzy-ament-cmake-clang-format \
        ros-jazzy-ament-cmake-clang-tidy \
        ros-jazzy-ament-cmake-ros \
        ros-jazzy-ament-cmake-test \
        ros-jazzy-controller-manager \
        ros-jazzy-ros2-control-test-assets \
        ros-jazzy-hardware-interface \
        ros-jazzy-example-interfaces \
        ros-jazzy-ros2-control-cmake \
        ros-jazzy-control-msgs \
        ros-jazzy-backward-ros \
        ros-jazzy-generate-parameter-library \
        ros-jazzy-realtime-tools \
        ros-jazzy-joint-state-publisher \
        ros-jazzy-joint-state-broadcaster \
        ros-jazzy-moveit-ros-move-group \
        ros-jazzy-moveit-kinematics \
        ros-jazzy-moveit-planners-ompl \
        ros-jazzy-moveit-ros-visualization \
        ros-jazzy-joint-trajectory-controller \
        ros-jazzy-moveit-simple-controller-manager \
        ros-jazzy-rviz2 \
        ros-jazzy-xacro \
        ros-jazzy-teleop-twist-keyboard \
        ros-jazzy-joy \
        ros-jazzy-teleop-twist-joy \
        ros-jazzy-rmw-cyclonedds-cpp \
    && sudo apt-get clean \
    && sudo rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws
COPY ./dependency.repos ./dependency.repos
RUN echo 'source /opt/ros/jazzy/setup.bash' >> /home/$USERNAME/.bashrc

# Set the default shell to bash and the workdir to the source directory
SHELL [ "/bin/bash", "-c" ]
CMD [ "/bin/bash" ]
WORKDIR /ros2_ws