"""
PookieBot Vision Pipeline
=========================
Provides seamless Sim-to-Real visual perception:
  1. 'sim'  mode: Renders offscreen RGB frames from MuJoCo 'robot_eye_camera'.
  2. 'real' mode: Streams live frames from phone webcam via OpenCV.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
import numpy as np


class BaseVision(ABC):
    """Abstract vision sensor interface."""

    @abstractmethod
    def capture_frame(self) -> np.ndarray:
        """Capture and return current RGB frame as (H, W, 3) uint8 numpy array."""
        pass

    def save_frame(self, filepath: str) -> bool:
        """Save captured frame to disk."""
        import cv2
        frame_rgb = self.capture_frame()
        if frame_rgb is None or frame_rgb.size == 0:
            return False
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        # Convert RGB to BGR for OpenCV
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        return cv2.imwrite(filepath, frame_bgr)

    def analyze_scene_heuristics(self) -> Dict[str, Any]:
        """
        Lightweight visual scene heuristics (brightness, dominant color, activity)
        used for quick reflex decisions before invoking heavy VLM queries.
        """
        frame = self.capture_frame()
        if frame is None:
            return {"status": "no_frame"}

        avg_brightness = float(np.mean(frame))
        r_mean = float(np.mean(frame[:, :, 0]))
        g_mean = float(np.mean(frame[:, :, 1]))
        b_mean = float(np.mean(frame[:, :, 2]))

        # Check for warm/calm lighting (nursery ambiance)
        is_dark = avg_brightness < 40.0
        is_warm = (r_mean > b_mean * 1.2)

        return {
            "status": "ok",
            "brightness": round(avg_brightness, 1),
            "is_dark": is_dark,
            "is_warm_light": is_warm,
            "mean_rgb": [round(r_mean, 1), round(g_mean, 1), round(b_mean, 1)]
        }


class SimVision(BaseVision):
    """
    Simulation vision pipeline utilizing MuJoCo's hardware-accelerated offscreen renderer.
    Renders from the 'robot_eye_camera' attached to the smartphone mount.
    """

    def __init__(self, model, data, camera_name: str = "robot_eye_camera", width: int = 640, height: int = 480):
        import mujoco
        self.model = model
        self.data = data
        self.camera_name = camera_name
        self.width = width
        self.height = height
        self.renderer = mujoco.Renderer(model, height=height, width=width)

    def capture_frame(self) -> np.ndarray:
        """Render high-fidelity offscreen frame from camera."""
        self.renderer.update_scene(self.data, camera=self.camera_name)
        return self.renderer.render()


class RealVision(BaseVision):
    """
    Physical robot vision capturing frames from smartphone IP stream or USB webcam.
    """

    def __init__(self, source: Any = 0, width: int = 640, height: int = 480):
        import cv2
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture frame from camera feed."""
        import cv2
        if not self.cap or not self.cap.isOpened():
            return None
        ret, frame_bgr = self.cap.read()
        if not ret:
            return None
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    def release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()


def get_vision(mode: str = "sim", **kwargs) -> BaseVision:
    """Factory helper to obtain either SimVision or RealVision."""
    if mode.lower() == "sim":
        return SimVision(**kwargs)
    elif mode.lower() == "real":
        return RealVision(**kwargs)
    else:
        raise ValueError(f"Unknown vision mode: '{mode}'")
