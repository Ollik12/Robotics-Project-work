"""Identify and order ArUco tags for the real side-camera workspace mask."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import rclpy
import yaml
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_SRC_DIR = SCRIPT_DIR.parent
CRISP_PY_DIR = SCRIPT_DIR.parents[1] / "crisp_py"
sys.path.insert(0, str(CRISP_PY_DIR))

from crisp_py.camera.aruco_workspace import make_aruco_detector  # noqa: E402


DEFAULT_CONFIG = REPO_SRC_DIR / "config" / "envs" / "franka_fm_real.yaml"
DEFAULT_TOPIC = "/camera/side_camera/color/image_raw/compressed"
WINDOW_NAME = "Side-camera ArUco calibration"


class WorkspaceCalibrator(Node):
    """Display detected tag IDs and collect their polygon order."""

    def __init__(self, topic: str, dictionary: str) -> None:
        """Create a ROS subscriber and a detector for the selected dictionary."""
        super().__init__("aruco_workspace_calibrator")
        self._detector = make_aruco_detector(dictionary)
        self._latest_frame: np.ndarray | None = None
        self._detections: dict[int, tuple[float, float]] = {}
        self._selected_id: int | None = None
        self._ordered_ids: dict[int, int] = {}
        self._subscription = self.create_subscription(
            CompressedImage,
            topic,
            self._image_callback,
            qos_profile_sensor_data,
        )

    def _image_callback(self, message: CompressedImage) -> None:
        encoded = np.frombuffer(message.data, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None:
            self.get_logger().warning("Could not decode a compressed camera frame.")
            return
        self._latest_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def run(self, config_path: Path, dictionary: str, write_config: bool) -> int:
        print(
            "Click a detected tag, then press 1-4 to assign its position clockwise "
            "around the workspace (start at any corner). Press s to finish, "
            "r to reset, or q to quit."
        )
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse_click)
        try:
            while rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.02)
                frame = self._latest_frame
                if frame is None:
                    display = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(
                        display,
                        f"Waiting for images on {self._subscription.topic_name}",
                        (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        1,
                    )
                else:
                    self._detections = self._detector(frame)
                    display = self._draw_status(frame.copy())

                cv2.imshow(WINDOW_NAME, cv2.cvtColor(display, cv2.COLOR_RGB2BGR))
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    return 0
                if key == ord("r"):
                    self._ordered_ids.clear()
                    self._selected_id = None
                if key in (ord("1"), ord("2"), ord("3"), ord("4")):
                    if self._selected_id is None:
                        print("Click a detected tag before assigning a position.")
                    else:
                        position = key - ord("0")
                        self._ordered_ids[position] = self._selected_id
                        print(f"Position {position}: marker ID {self._selected_id}")
                if key == ord("s"):
                    if self._finish(config_path, dictionary, write_config):
                        return 0
        finally:
            cv2.destroyWindow(WINDOW_NAME)
        return 0

    def _on_mouse_click(
        self, event: int, x: int, y: int, flags: int, data: object
    ) -> None:
        if event != cv2.EVENT_LBUTTONDOWN or not self._detections:
            return
        nearest_id, nearest_center = min(
            self._detections.items(),
            key=lambda item: (item[1][0] - x) ** 2 + (item[1][1] - y) ** 2,
        )
        distance = np.hypot(nearest_center[0] - x, nearest_center[1] - y)
        if distance <= 40:
            self._selected_id = nearest_id
            print(f"Selected marker ID {nearest_id}")
        else:
            self._selected_id = None

    def _draw_status(self, image: np.ndarray) -> np.ndarray:
        for marker_id, center in self._detections.items():
            point = tuple(np.rint(center).astype(int))
            color = (0, 255, 0) if marker_id == self._selected_id else (255, 255, 0)
            cv2.circle(image, point, 7, color, 2)
            cv2.putText(
                image,
                f"ID {marker_id}",
                (point[0] + 8, point[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        assignments = "  ".join(
            f"{position}: {self._ordered_ids.get(position, '-')}"
            for position in range(1, 5)
        )
        cv2.putText(
            image,
            "Click tag + press 1-4 clockwise | s save | r reset | q quit",
            (12, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            image,
            f"Ordered IDs: {assignments}",
            (12, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )
        return image

    def _finish(self, config_path: Path, dictionary: str, write_config: bool) -> bool:
        ordered_ids = [self._ordered_ids.get(position) for position in range(1, 5)]
        if any(marker_id is None for marker_id in ordered_ids):
            print("Assign all four positions before saving.")
            return False
        if len(set(ordered_ids)) != 4:
            print("Each position must use a different marker ID.")
            return False

        ids = [int(marker_id) for marker_id in ordered_ids]
        print(f"workspace_aruco_ids: {ids}")
        print(f'workspace_aruco_dictionary: "{dictionary}"')
        if write_config:
            update_config(config_path, ids, dictionary)
            print(f"Updated {config_path}")
        return True


def update_config(config_path: Path, marker_ids: list[int], dictionary: str) -> None:
    """Update only the side-camera ArUco settings, preserving other YAML text."""
    with config_path.open("r", encoding="utf-8", newline="") as file:
        text = file.read()
    config = yaml.safe_load(text)
    cameras = config.get("camera_configs") if isinstance(config, dict) else None
    if not isinstance(cameras, list) or not any(
        isinstance(camera, dict) and camera.get("camera_name") == "side_camera"
        for camera in cameras
    ):
        raise ValueError(f"No side_camera entry found in {config_path}")

    lines = text.splitlines()
    side_camera_pattern = re.compile(
        r'^(\s*)-\s*camera_name:\s*["\']?side_camera["\']?\s*$'
    )
    start = next(
        (index for index, line in enumerate(lines) if side_camera_pattern.match(line)),
        None,
    )
    if start is None:
        raise ValueError(f"Could not locate side_camera in {config_path}")

    entry_indent = len(side_camera_pattern.match(lines[start]).group(1))
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            continue
        line_indent = len(lines[index]) - len(lines[index].lstrip())
        if line_indent < entry_indent or (
            line_indent == entry_indent and stripped.startswith("-")
        ):
            end = index
            break
    key_indent = " " * (entry_indent + 2)
    replacements = {
        "workspace_aruco_ids": f"{key_indent}workspace_aruco_ids: {marker_ids}",
        "workspace_aruco_dictionary": (
            f'{key_indent}workspace_aruco_dictionary: "{dictionary}"'
        ),
    }

    for key, replacement in replacements.items():
        key_pattern = re.compile(rf"^\s*{re.escape(key)}\s*:")
        existing = next(
            (
                index
                for index in range(start + 1, end)
                if key_pattern.match(lines[index])
            ),
            None,
        )
        if existing is None:
            lines.insert(end, replacement)
            end += 1
        else:
            lines[existing] = replacement

    newline = "\r\n" if "\r\n" in text else "\n"
    updated_text = newline.join(lines) + (
        newline if text.endswith(("\n", "\r")) else ""
    )
    with config_path.open("w", encoding="utf-8", newline="") as file:
        file.write(updated_text)
    updated_config = yaml.safe_load(updated_text)
    updated_camera = next(
        camera
        for camera in updated_config["camera_configs"]
        if camera.get("camera_name") == "side_camera"
    )
    if (
        updated_camera.get("workspace_aruco_ids") != marker_ids
        or updated_camera.get("workspace_aruco_dictionary") != dictionary
    ):
        raise ValueError(f"Failed to verify updated ArUco settings in {config_path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show side-camera ArUco IDs and optionally write their workspace order."
    )
    parser.add_argument(
        "--topic", default=DEFAULT_TOPIC, help="Compressed side-camera topic."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dictionary", default="DICT_4X4_50")
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="Write the selected IDs and dictionary to the side_camera YAML entry.",
    )
    return parser


def main() -> int:
    """Run the interactive side-camera ArUco calibration tool."""
    args = _build_parser().parse_args()
    node: WorkspaceCalibrator | None = None
    try:
        rclpy.init()
        node = WorkspaceCalibrator(args.topic, args.dictionary)
        return node.run(args.config, args.dictionary, args.write_config)
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
