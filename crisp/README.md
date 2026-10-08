# CRISP Setup

> [!NOTE]
> `crisp_gym` will run inside Pixi environment with dedicated Robostack ROS2 version. Therefore, setup/run crisp outside the Franka Docker environment. CRISP and the Franka Docker ROS will communicate with each other via same `ROS_DOMAIN_ID` and using `rmw_cyclonedds_cpp`.

## 1. Install Pixi

Linux
```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

## 2. Clone `crisp_gym` 

Navigate to `crisp` directory and clone the `crisp_gym` repository
```bash
cd crisp
git clone git@github.com:learnsyslab/crisp_gym.git
```

## 3. Access Pixi shell and test installation

Access the CRISP Pixi shell from `crisp/` directory with:
```bash
pixi shell -e jazzy-lerobot
```

Test that the installation was successful. These should not print anything:
```bash
python -c "import crisp_gym"
python -c "import crisp_py"
```

## 4. Apply `record_functions.py` patch

`patches/` directory contains `record_functions.py` which is modified version from the one that comes with `crisp_gym`. There was a small bug and it has been fixed on that file. Replace `crisp_gym/crisp_gym/record/record_functions.py` with `patches/record_functions.py` file.

Issue was that the original file tried to access `gripper.value` but the `TeleopStreamedPose` class has property `last_gripper`. So I changed `line 78`:
```
gripper = leader.gripper.value if leader.gripper is not None else 0.0
```
to
```
gripper = leader.gripper.last_gripper if leader.last_gripper is not None else 0.0
```

## Teleoperation with CRISP

> [!NOTE]
> This currently works only with PS5 teleoperation but will be implemented for other teleoperation devices too (HTC Vive, keyboard etc.). This is currently just a small script/PoC implementation which verifies that Gazebo Franka can be controlled with CRISP.

### 2. Copy config

Copy the config `franka_fm.yaml` included in `crisp/src/config/envs` to the `crisp_gym/crisp_gym/config/envs` directory

### 3. Run Gazebo

In Docker terminal run the Gazebo simulation environment with:
```bash
ros2 launch franka_fm_gazebo sim.launch.py
```

### 4. Run PS5 teleop node

In another Docker terminal launch PS5 teleop node with `--crisp-teleop` argument
```bash
ros2 run franka_fm_teleop ps5_teleop_node --crisp-teleop
```

### 5. Run CRISP teleop script

Finally, run in Pixi/CRISP terminal script which is located in `crisp/src/teleop/crisp_teleop.py`. Navigate to that directory in your terminal and run:
```bash
python crisp_teleop.py
```

It should print these is everything is OK and then the teleoperation should work:
```
Environment created
Target initialized
Teleop is ready
```

## 6. Record LeRobot data

### 1. In Docker terminal run the Gazebo simulation environment with:
```bash
ros2 launch franka_fm_gazebo sim.launch.py
```
### 2. In another Docker terminal launch PS5 teleop node with `--crisp-teleop` argument
```bash
ros2 run franka_fm_teleop ps5_teleop_node --crisp-teleop
```

### 3. In Pixi/CRISP terminal navigate to `crisp/src/record` directory and run `record_teleop.py`

Script accepts multiple arguments but here is one example for testing

```bash
python record_teleop.py --tasks 'Pick the green cube and place it on the blue surface' --fps 25 --num-episodes 1 
```
By running that, the script should initialize the recording and waits until user presses `r` to start the teleop and recording. By pressing `r` again, it asks whether
the user wants to save/delete the recorded episode by pressing `s`/`d`. Press `s` and the episode should be saved. 

Script saves the episode(s) automatically into `/home/<username>/.cache/huggingface/lerobot` directory. 

If you want to record episodes and push them into hugging face you must give arguments `--repo-id <username>/<repo-id>` and `--push-to-hub true`. However, that is not mandatory
since the episodes can be saved locally and pushed into hugging face hub afterwards.

## 7. Hugging Face hub CLI configuration

### 1. Install hf CLI with:

```
curl -LsSf https://hf.co/cli/install.sh | bash
```

### 2. Create Access Token

Login to [Hugging Face](https://huggingface.co)

Go to Settings > Access Token and create new access token and copy the value

From terminal use
```bash
hf auth login
```
And paste the token value when prompted

## 8. Push datasets manually into HF hub

### 1. Create dataset repo to HF hub

### 2. Copy dataset (optional)
Once you have successfully recorded dataset and setup the hf CLI authentication, you can copy the data set from
`/home/<username>/.cache/huggingface/lerobot` to e.g. `/home/<username>`, open terminal in that directory

### 3. Push data to HF repo

```bash
hf upload <username>/<repo-id> . --repo-type=dataset
```
### Example dataset

An example dataset recorded with this setup can be found from [fr3-gz](https://huggingface.co/datasets/iikkao/fr3-gz)

## 📝 TODO:
- Implement CRISP teleoperation nodes for other devices such as HTC Vive, 3D Mouse, keyboard etc. / whatever device we will use for teleoperating the real Franka in the future
- Check gripper observation state (why it stays at value 1 in all datasets)
- Improve data collection workflow and maybe home pos, surface, cube position could vary between episodes
    - Add random pos generation with small range
    - Robot reset node improvement
    
## Issues:
- CRISP ROS2 is using older controller_manager 4.25 while the Docker ROS2 has 4.48. Therefore we cannot use e.g. robot.home() because it requires controller switching.
- CRISP side homing would be useful because that could be called immediately after stopping the episode recording from CRISP recording script.
- There is a separate ROS2 package `franka_fm_reset` which can be used for resetting the robot and Gazebo between episodes, but when it has finished the homing and switches back to cartesian controller the CRISP side somehow publishes the old target position for the controller and the robot is controlled there immediately.
- After reset, the teleop node starts publishing the home position so it should update to the CRISP TeleopStreamedPose also.
- Proposed solution: downgrade Docker controller_manager / investigate what causes that the CRISP side does not update the target position after the reset node is run.

# Architecture idea:
![Environment architecture](/crisp/images/franka_fm_crisp.png)
