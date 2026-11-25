"""Mask camera images to a workspace polygon calibrated by ArUco markers."""

from collections.abc import Callable, Mapping
from threading import Lock

import cv2
import numpy as np

MarkerCenters = Mapping[int, tuple[float, float]]


class ArucoWorkspaceMask:
    """Keep only the polygon defined by four ordered ArUco marker centers."""

    def __init__(
        self,
        marker_ids: list[int],
        dictionary_name: str,
        *,
        detector: Callable[[np.ndarray], MarkerCenters] | None = None,
    ) -> None:
        """Create a mask for four ordered marker IDs and their dictionary."""
        if len(marker_ids) != 4 or len(set(marker_ids)) != 4:
            raise ValueError("workspace_aruco_ids must contain four unique marker IDs.")
        if any(isinstance(marker_id, bool) or marker_id < 0 for marker_id in marker_ids):
            raise ValueError("workspace_aruco_ids must contain non-negative integers.")

        self.marker_ids = tuple(marker_ids)
        self._polygon: np.ndarray | None = None
        self._detector = detector or make_aruco_detector(dictionary_name)
        self._lock = Lock()

    @property
    def is_calibrated(self) -> bool:
        """Return whether a complete workspace polygon has been observed."""
        return self._polygon is not None

    def apply(self, image: np.ndarray) -> np.ndarray:
        """Mask an image, returning black until all four markers are calibrated."""
        with self._lock:
            if self._polygon is None:
                centers = self._detector(image)
                if not all(marker_id in centers for marker_id in self.marker_ids):
                    return np.zeros_like(image)

                polygon = np.asarray(
                    [centers[marker_id] for marker_id in self.marker_ids],
                    dtype=np.float32,
                )
                if not self._is_valid_polygon(polygon):
                    return np.zeros_like(image)
                self._polygon = np.rint(polygon).astype(np.int32)

            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.fillPoly(mask, [self._polygon], 255)
            return cv2.bitwise_and(image, image, mask=mask)

    @staticmethod
    def _is_valid_polygon(polygon: np.ndarray) -> bool:
        edges = np.roll(polygon, -1, axis=0) - polygon
        following_edges = np.roll(edges, -1, axis=0)
        cross_products = edges[:, 0] * following_edges[:, 1] - edges[:, 1] * following_edges[:, 0]
        return bool(np.all(cross_products > 0) or np.all(cross_products < 0))


def make_aruco_detector(dictionary_name: str) -> Callable[[np.ndarray], MarkerCenters]:
    """Create a detector returning each visible marker ID and image center."""
    aruco = getattr(cv2, "aruco", None)
    if aruco is None:
        raise RuntimeError(
            "ArUco workspace masking requires OpenCV's aruco module (opencv-contrib)."
        )
    if not hasattr(aruco, dictionary_name):
        raise ValueError(f"Unknown ArUco dictionary: {dictionary_name}")

    dictionary = aruco.getPredefinedDictionary(getattr(aruco, dictionary_name))
    if hasattr(aruco, "ArucoDetector"):
        marker_detector = aruco.ArucoDetector(dictionary, aruco.DetectorParameters())

        def detect(image: np.ndarray) -> MarkerCenters:
            corners, ids, _ = marker_detector.detectMarkers(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))
            return _centers_by_id(corners, ids)

        return detect

    parameters = aruco.DetectorParameters_create()

    def detect_legacy(image: np.ndarray) -> MarkerCenters:
        corners, ids, _ = aruco.detectMarkers(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY),
            dictionary,
            parameters=parameters,
        )
        return _centers_by_id(corners, ids)

    return detect_legacy


def _centers_by_id(corners: list[np.ndarray], ids: np.ndarray | None) -> MarkerCenters:
    if ids is None:
        return {}
    return {
        int(marker_id): tuple(np.asarray(marker_corners).reshape(4, 2).mean(axis=0))
        for marker_corners, marker_id in zip(corners, ids.flatten(), strict=True)
    }
