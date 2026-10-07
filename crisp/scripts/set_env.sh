export GIT_LFS_SKIP_SMUDGE=1  
export SVT_LOG=1  
export ROS_DOMAIN_ID=100
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

ros2 daemon stop && ros2 daemon start
