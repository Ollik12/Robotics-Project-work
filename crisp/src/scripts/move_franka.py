import time

from crisp_py.robot import make_robot

robot = make_robot("fr3")
robot.wait_until_ready()  # make sure that all topics have been received
time.sleep(1.0)  # wait for the robot to be ready

# %% First home
robot.home()  # will activate a joint trajectory controller and home the robot

# %% Check state
print(robot.end_effector_pose)
print(robot.joint_values)


# %% Activate cartesian impedance controller
robot.controller_switcher_client.switch_controller("cartesian_impedance_controller")