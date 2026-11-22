"""
PookieBot Visual Servoing & Object Grounding
============================================
Implements Image-Based Visual Servoing (IBVS) and spatial object grounding:
  1. Multi-target visual perception (Color segmentation, Contour tracking, ArUco fiducials).
  2. Closed-loop proportional-derivative visual servoing controller.
  3. Automatic 360-degree exploratory sweep / acquisition when targets are out of view.
  4. Sim-to-Real parity: Works interchangeably on MuJoCo simulated camera or physical phone webcam.
"""

import math
import time
from enum import Enum
from typing import Dict, Any, Optional, Tuple, List, Callable
import numpy as np
import cv2


class TargetType(str, Enum):
    RED_CUBE = "red_cube"
    YELLOW_BALL = "yellow_ball"
    GREEN_BOTTLE = "green_bottle"
    BLUE_BOX = "blue_box"
    DOCKING_STATION = "docking_station"
    ARUCO = "aruco"


# Natural language aliases mapping colloquial phrases to targets
TARGET_ALIASES = {
    "red cube": TargetType.RED_CUBE,
    "cube": TargetType.RED_CUBE,
    "red block": TargetType.RED_CUBE,
    "block": TargetType.RED_CUBE,
    "red": TargetType.RED_CUBE,
    
    "yellow ball": TargetType.YELLOW_BALL,
    "ball": TargetType.YELLOW_BALL,
    "yellow sphere": TargetType.YELLOW_BALL,
    "yellow": TargetType.YELLOW_BALL,
    
    "green bottle": TargetType.GREEN_BOTTLE,
    "bottle": TargetType.GREEN_BOTTLE,
    "milk bottle": TargetType.GREEN_BOTTLE,
    "green": TargetType.GREEN_BOTTLE,
    
    "blue box": TargetType.BLUE_BOX,
    "blue toy": TargetType.BLUE_BOX,
    "toy box": TargetType.BLUE_BOX,
    "toybox": TargetType.BLUE_BOX,
    "blue": TargetType.BLUE_BOX,
    
    "dock": TargetType.DOCKING_STATION,
    "docking station": TargetType.DOCKING_STATION,
    "charging station": TargetType.DOCKING_STATION,
    "charger": TargetType.DOCKING_STATION,
    "home": TargetType.DOCKING_STATION,
    "aruco": TargetType.ARUCO,
}


class TargetDetector:
    """
    Perception engine detecting color-coded objects and ArUco fiducial markers.
    """

    def __init__(self):
        # ArUco detector setup
        self.dict_aruco = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(self.dict_aruco, self.aruco_params)

    @staticmethod
    def resolve_target(name: str) -> Optional[TargetType]:
        """Convert natural language string into TargetType enum."""
        name_clean = name.strip().lower()
        if name_clean in TARGET_ALIASES:
            return TARGET_ALIASES[name_clean]
        for key, val in TARGET_ALIASES.items():
            if key in name_clean:
                return val
        return None

    def detect(self, frame_rgb: np.ndarray, target: TargetType) -> Dict[str, Any]:
        """
        Detect specified target in RGB frame.
        Returns dictionary:
          - found: bool
          - centroid: (cx, cy) in pixels
          - error_x: normalized horizontal offset [-1.0 (left), 1.0 (right)]
          - area: pixel area
          - bbox: (x, y, w, h)
        """
        if frame_rgb is None or frame_rgb.size == 0:
            return {"found": False, "target": target.value}

        height, width, _ = frame_rgb.shape
        center_x = width / 2.0

        if target in (TargetType.DOCKING_STATION, TargetType.ARUCO):
            return self._detect_aruco(frame_rgb, width, height, center_x)
        else:
            return self._detect_color(frame_rgb, target, width, height, center_x)

    def _detect_aruco(self, frame_rgb: np.ndarray, width: int, height: int, center_x: float) -> Dict[str, Any]:
        gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
        corners, ids, _ = self.aruco_detector.detectMarkers(gray)
        if ids is not None and len(ids) > 0:
            c = corners[0][0] if len(corners[0].shape) == 2 else corners[0]
            cx = float(np.mean(c[:, 0]))
            cy = float(np.mean(c[:, 1]))
            w = float(np.max(c[:, 0]) - np.min(c[:, 0]))
            h = float(np.max(c[:, 1]) - np.min(c[:, 1]))
            err_x = (cx - center_x) / center_x
            marker_id = int(np.array(ids).flatten()[0])
            return {
                "found": True,
                "target": TargetType.DOCKING_STATION.value,
                "marker_id": marker_id,
                "centroid": (round(cx, 1), round(cy, 1)),
                "error_x": round(err_x, 3),
                "bbox": (int(cx - w / 2), int(cy - h / 2), int(w), int(h)),
                "area": int(w * h),
            }
        return {"found": False, "target": TargetType.DOCKING_STATION.value}

    def _detect_color(self, frame_rgb: np.ndarray, target: TargetType, width: int, height: int, center_x: float) -> Dict[str, Any]:
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

        if target == TargetType.RED_CUBE:
            # Red wraps around 0 and 180 in HSV
            mask1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([12, 255, 255]))
            mask2 = cv2.inRange(hsv, np.array([168, 80, 80]), np.array([180, 255, 255]))
            mask = mask1 | mask2
            min_area = 150

        elif target == TargetType.YELLOW_BALL:
            mask = cv2.inRange(hsv, np.array([16, 90, 90]), np.array([36, 255, 255]))
            min_area = 120

        elif target == TargetType.GREEN_BOTTLE:
            mask = cv2.inRange(hsv, np.array([38, 80, 80]), np.array([85, 255, 255]))
            min_area = 120

        elif target == TargetType.BLUE_BOX:
            # Restrict to bottom 75% of frame to avoid background skybox blue
            mask = cv2.inRange(hsv, np.array([95, 110, 80]), np.array([135, 255, 255]))
            mask[: int(height * 0.25), :] = 0
            min_area = 200
        else:
            return {"found": False, "target": target.value}

        # Morphological opening to clean small noise specks
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return {"found": False, "target": target.value}

        # Pick the largest contour
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < min_area:
            return {"found": False, "target": target.value}

        M = cv2.moments(largest)
        if M["m00"] == 0:
            return {"found": False, "target": target.value}

        cx = float(M["m10"] / M["m00"])
        cy = float(M["m01"] / M["m00"])
        x, y, w, h = cv2.boundingRect(largest)
        err_x = (cx - center_x) / center_x

        return {
            "found": True,
            "target": target.value,
            "centroid": (round(cx, 1), round(cy, 1)),
            "error_x": round(err_x, 3),
            "bbox": (int(x), int(y), int(w), int(h)),
            "area": int(area),
        }


class VisualServoingController:
    """
    Closed-loop Image-Based Visual Servoing (IBVS) Controller.
    Steers the 4WD chassis to center the target in frame and drives forward
    until the ultrasonic rangefinder detects the target at the stopping distance.
    """

    def __init__(
        self,
        bridge,
        vision,
        step_sim_fn: Optional[Callable[[], None]] = None,
        kp_yaw: float = 90.0,
        kd_yaw: float = 20.0,
        base_speed_pwm: float = 110.0,
    ):
        self.bridge = bridge
        self.vision = vision
        self.step_sim_fn = step_sim_fn
        self.detector = TargetDetector()
        self.kp_yaw = kp_yaw
        self.kd_yaw = kd_yaw
        self.base_speed = base_speed_pwm

    def navigate_to_target(
        self,
        target_name: str,
        stop_dist_m: float = 0.22,
        max_duration_s: float = 15.0,
        face_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Full autonomous navigation pipeline to named target:
          1. Resolve target.
          2. Sweep/turn if target is not initially visible.
          3. Continuous visual servoing: compute normalized error and apply proportional differential steering.
          4. Halt smoothly when HC-SR04 sonar reaches stop_dist_m.
        """
        target = self.detector.resolve_target(target_name)
        if target is None:
            return {
                "success": False,
                "reason": f"Unknown target '{target_name}'. Available: red cube, yellow ball, green bottle, blue box, dock.",
            }

        if face_callback:
            face_callback("CURIOUS", f"Looking for the {target.value.replace('_', ' ')}...")

        # Step 1: Initial Acquisition
        frame = self.vision.capture_frame()
        det = self.detector.detect(frame, target)

        if not det["found"]:
            # Perform exploratory scan (rotate slowly to search)
            found = self._exploratory_scan(target, max_scan_steps=80)
            if not found:
                if face_callback:
                    face_callback("ALERT", f"Could not find {target.value.replace('_', ' ')} in the room!")
                return {"success": False, "reason": f"Target '{target.value}' not found in 360-degree sweep."}

        if face_callback:
            face_callback("HAPPY", f"Found the {target.value.replace('_', ' ')}! Approaching now.")

        # Step 2: Visual Servoing Control Loop
        start_time = time.time()
        prev_error_x = 0.0
        consecutive_lost = 0
        total_steps = 0

        while True:
            # Step bridge control logic and physics
            self.bridge.step()
            if self.step_sim_fn:
                for _ in range(3):
                    self.step_sim_fn()
            else:
                time.sleep(0.015)

            total_steps += 1
            sonar_m = self.bridge.get_sonar_distance()

            # Stopping condition 1: Sonar reach
            if sonar_m <= stop_dist_m:
                self.bridge.stop()
                if face_callback:
                    face_callback("LOVING", f"Arrived at {target.value.replace('_', ' ')}! Distance: {sonar_m*100:.1f}cm.")
                return {
                    "success": True,
                    "target": target.value,
                    "final_sonar_m": round(sonar_m, 3),
                    "steps": total_steps,
                    "reason": "Arrived at target distance.",
                }

            # Stopping condition 2: Hardware safety cutoff
            if self.bridge.is_safety_stop_active():
                self.bridge.stop()
                if face_callback:
                    face_callback("ALERT", "Safety stop engaged.")
                return {
                    "success": True,
                    "target": target.value,
                    "final_sonar_m": round(sonar_m, 3),
                    "steps": total_steps,
                    "reason": "Safety stop limit reached.",
                }

            # Check timeout
            if time.time() - start_time > max_duration_s and not self.step_sim_fn:
                self.bridge.stop()
                return {"success": False, "reason": "Navigation timeout exceeded."}

            if self.step_sim_fn and total_steps > int(max_duration_s / 0.015):
                self.bridge.stop()
                return {"success": False, "reason": "Simulation step budget exceeded."}

            # Capture visual frame and track
            frame = self.vision.capture_frame()
            det = self.detector.detect(frame, target)

            if not det["found"]:
                consecutive_lost += 1
                if consecutive_lost > 15:
                    # Lost target: pause and re-scan
                    self.bridge.stop()
                    found = self._exploratory_scan(target, max_scan_steps=40)
                    if not found:
                        return {"success": False, "reason": "Target lost during tracking."}
                    consecutive_lost = 0
                continue

            consecutive_lost = 0
            err_x = det["error_x"]
            d_err = err_x - prev_error_x
            prev_error_x = err_x

            # Stopping condition 3: Target occupies large portion of camera view (close proximity fallback)
            if det["bbox"][2] > (frame.shape[1] * 0.35):
                self.bridge.stop()
                return {
                    "success": True,
                    "target": target.value,
                    "final_sonar_m": round(sonar_m, 3),
                    "steps": total_steps,
                    "reason": "Visual bounding box threshold reached.",
                }

            # Steering Control: PD Controller on horizontal error
            yaw_cmd = (self.kp_yaw * err_x) + (self.kd_yaw * d_err)

            # Modulate forward speed: slow down when turning sharply
            alignment_factor = max(0.2, 1.0 - abs(err_x))
            v_forward = self.base_speed * alignment_factor

            # Proportional differential drive allocation
            left_pwm = float(np.clip(v_forward + yaw_cmd, -255, 255))
            right_pwm = float(np.clip(v_forward - yaw_cmd, -255, 255))

            self.bridge.send_motors(left_pwm, right_pwm)

    def _exploratory_scan(self, target: TargetType, max_scan_steps: int = 60) -> bool:
        """Gently rotate in place to sweep 360 degrees and acquire target."""
        # Spin counter-clockwise slowly (left = -110, right = +110)
        for _ in range(max_scan_steps):
            self.bridge.send_motors(-110, 110)
            self.bridge.step()
            if self.step_sim_fn:
                for _ in range(3):
                    self.step_sim_fn()
            else:
                time.sleep(0.015)

            frame = self.vision.capture_frame()
            det = self.detector.detect(frame, target)
            if det["found"] and abs(det["error_x"]) < 0.4:
                self.bridge.stop()
                return True

        self.bridge.stop()
        return False


# =====================================================================
# Standalone Unit Test
# =====================================================================
if __name__ == "__main__":
    import os
    import mujoco
    from core.hal import SimRobotBridge
    from core.vision import SimVision

    print("=== Testing PookieBot Visual Servoing & Perception ===")
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "simulation", "models", "pookiebot.xml")
    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    bridge = SimRobotBridge(model, data)
    vision = SimVision(model, data, camera_name="robot_eye_camera")

    detector = TargetDetector()
    frame = vision.capture_frame()

    print("\n1. Testing Object Perception from Camera View:")
    for target in [TargetType.RED_CUBE, TargetType.YELLOW_BALL, TargetType.GREEN_BOTTLE, TargetType.DOCKING_STATION]:
        res = detector.detect(frame, target)
        print(f"  Target '{target.value}': found={res['found']}, centroid={res.get('centroid')}, error_x={res.get('error_x')}")

    print("\n2. Testing Autonomous Visual Servoing Navigation to 'red cube':")
    def sim_step():
        mujoco.mj_step(model, data)

    controller = VisualServoingController(bridge, vision, step_sim_fn=sim_step)
    result = controller.navigate_to_target("red cube", stop_dist_m=0.22)
    print(f"  Result: {result}")
    assert result["success"], "Visual servoing failed to navigate to red cube!"

    print("\n✅ Visual Servoing Standalone Verification Passed Successfully!")
