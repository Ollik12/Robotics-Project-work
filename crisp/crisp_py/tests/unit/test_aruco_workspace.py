"""Tests for side-camera workspace polygon masking."""

from unittest.mock import Mock

import numpy as np

from crisp_py.camera.aruco_workspace import ArucoWorkspaceMask


def test_masks_pixels_outside_calibrated_polygon():
    """Keep polygon pixels while blacking out the image exterior."""
    detector = Mock(
        return_value={
            10: (2, 2),
            11: (7, 2),
            12: (7, 7),
            13: (2, 7),
        }
    )
    workspace = ArucoWorkspaceMask([10, 11, 12, 13], "DICT_4X4_50", detector=detector)
    image = np.full((10, 10, 3), 255, dtype=np.uint8)

    result = workspace.apply(image)

    assert workspace.is_calibrated
    assert np.all(result[4, 4] == 255)
    assert np.all(result[0, 0] == 0)


def test_waits_for_all_markers_then_retains_polygon_when_a_marker_is_occluded():
    """Wait for a complete calibration and then retain the static polygon."""
    detections = [
        {0: (2, 2), 1: (7, 2), 2: (7, 7)},
        {0: (2, 2), 1: (7, 2), 2: (7, 7), 3: (2, 7)},
    ]
    detector = Mock(side_effect=detections)
    workspace = ArucoWorkspaceMask([0, 1, 2, 3], "DICT_4X4_50", detector=detector)
    image = np.full((10, 10, 3), 255, dtype=np.uint8)

    uncalibrated = workspace.apply(image)
    calibrated = workspace.apply(image)
    occluded = workspace.apply(image)

    assert workspace.is_calibrated
    assert np.all(uncalibrated == 0)
    assert np.array_equal(calibrated, occluded)
    assert detector.call_count == 2
