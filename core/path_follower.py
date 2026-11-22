"""
PookieBot Pure Pursuit Path Following Controller
================================================
Implements Pure Pursuit trajectory tracking for 2D waypoints:
  1. Finds lookahead target along the user-drawn path polyline.
  2. Computes curvature arc and differential steering allocation.
  3. Seamlessly handles touch/mouse trajectories drawn on the smartphone Web UI.
  4. 1:1 Sim-to-Real parity: Works with both SimRobotBridge and RealRobotBridge.
"""

import math
import time
from typing import List, Tuple, Dict, Any, Optional, Callable
import numpy as np


class PurePursuitController:
    """
    Pure Pursuit path tracker for differential drive chassis.
    """

    def __init__(
        self,
        bridge,
        step_sim_fn: Optional[Callable[[], None]] = None,
        lookahead_m: float = 0.28,
        base_speed_pwm: float = 120.0,
        goal_tolerance_m: float = 0.16,
        track_width_m: float = 0.15,
        steer_gain: float = 45.0,
    ):
        self.bridge = bridge
        self.step_sim_fn = step_sim_fn
        self.lookahead_m = lookahead_m
        self.base_speed = base_speed_pwm
        self.goal_tolerance = goal_tolerance_m
        self.track_width = track_width_m
        self.steer_gain = steer_gain

    def follow_path(
        self,
        waypoints: List[Tuple[float, float]],
        max_duration_s: float = 25.0,
        face_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Execute path tracking along a list of 2D waypoints [(x0, y0), (x1, y1), ...].
        """
        if not waypoints or len(waypoints) < 2:
            return {"success": False, "reason": "Path must contain at least 2 waypoints."}

        pts = np.array(waypoints, dtype=float)
        goal_pt = pts[-1]

        if face_callback:
            face_callback("CURIOUS", f"Starting path following ({len(pts)} waypoints)...")

        start_time = time.time()
        total_steps = 0
        path_idx = 0

        while True:
            # Step control and physics
            self.bridge.step()
            if self.step_sim_fn:
                for _ in range(3):
                    self.step_sim_fn()
            else:
                time.sleep(0.015)

            total_steps += 1
            curr_x, curr_y, curr_yaw = self.bridge.get_pose()

            # 1. Check distance to final goal
            dist_to_final = math.hypot(goal_pt[0] - curr_x, goal_pt[1] - curr_y)
            if dist_to_final <= self.goal_tolerance:
                self.bridge.stop()
                if face_callback:
                    face_callback("HAPPY", f"Completed drawn trajectory in {total_steps} steps!")
                return {
                    "success": True,
                    "final_dist_to_goal": round(dist_to_final, 3),
                    "steps": total_steps,
                    "reason": "Reached destination waypoint.",
                }

            # 2. Check obstacle safety stop
            if self.bridge.is_safety_stop_active():
                self.bridge.stop()
                if face_callback:
                    face_callback("ALERT", "Obstacle encountered along drawn path!")
                return {
                    "success": False,
                    "reason": "Safety obstacle stop engaged along path.",
                    "steps": total_steps,
                }

            # 3. Check timeout
            if not self.step_sim_fn and (time.time() - start_time > max_duration_s):
                self.bridge.stop()
                return {"success": False, "reason": "Path following timeout."}

            if self.step_sim_fn and total_steps > int(max_duration_s / 0.015):
                self.bridge.stop()
                return {"success": False, "reason": "Step budget exceeded."}

            # 4. Find Lookahead Target Point along path
            lookahead_target = self._find_lookahead_point(pts, curr_x, curr_y)

            # 5. Transform target to robot local frame
            dx = lookahead_target[0] - curr_x
            dy = lookahead_target[1] - curr_y

            # Rotate into robot heading frame
            # local_x is forward, local_y is left
            local_x = dx * math.cos(curr_yaw) + dy * math.sin(curr_yaw)
            local_y = -dx * math.sin(curr_yaw) + dy * math.cos(curr_yaw)

            # Lookahead distance from robot
            dist_to_target = math.hypot(local_x, local_y)
            if dist_to_target < 1e-4:
                continue

            # Heading error alpha
            alpha = math.atan2(local_y, local_x)

            # Pure pursuit curvature: kappa = 2 * sin(alpha) / L
            kappa = 2.0 * math.sin(alpha) / max(0.1, dist_to_target)

            # Modulate speed: slow down when turning sharply
            turn_slowdown = max(0.35, math.cos(alpha))
            speed = self.base_speed * turn_slowdown

            # Proportional yaw command
            steer = kappa * self.steer_gain

            left_pwm = float(np.clip(speed - steer, -220, 220))
            right_pwm = float(np.clip(speed + steer, -220, 220))

            self.bridge.send_motors(left_pwm, right_pwm)

    def _find_lookahead_point(self, pts: np.ndarray, curr_x: float, curr_y: float) -> np.ndarray:
        """
        Finds the point along the waypoint segments that lies at lookahead_m distance.
        """
        # Calculate distances from current position to all waypoints
        dists = np.hypot(pts[:, 0] - curr_x, pts[:, 1] - curr_y)
        closest_idx = int(np.argmin(dists))

        # Look forward along segments starting from closest index
        for i in range(closest_idx, len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            seg_vec = p2 - p1
            seg_len = float(np.linalg.norm(seg_vec))
            if seg_len < 1e-4:
                continue

            # Check if distance to p2 is beyond lookahead
            d2 = math.hypot(p2[0] - curr_x, p2[1] - curr_y)
            if d2 >= self.lookahead_m:
                # Interpolate lookahead point along segment
                ratio = max(0.0, min(1.0, (self.lookahead_m - dists[i]) / seg_len))
                return p1 + ratio * seg_vec

        # If near the end, target the final point directly
        return pts[-1]


# =====================================================================
# Standalone Unit Test
# =====================================================================
if __name__ == "__main__":
    import os
    import mujoco
    from core.hal import SimRobotBridge

    print("=== Testing PookieBot Pure Pursuit Path Follower ===")
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "simulation", "models", "pookiebot.xml")
    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    bridge = SimRobotBridge(model, data)

    def sim_step():
        mujoco.mj_step(model, data)

    controller = PurePursuitController(bridge, step_sim_fn=sim_step)

    # Test an S-curve path around the nursery
    test_path = [
        (0.0, 0.0),
        (0.3, 0.15),
        (0.6, 0.25),
        (0.9, 0.15),
        (1.1, -0.1),
    ]

    print(f"Executing test S-curve trajectory with {len(test_path)} waypoints...")
    res = controller.follow_path(test_path, max_duration_s=12.0)
    print(f"Result: {res}")
    assert res["success"], "Pure Pursuit failed to follow test path!"

    final_pose = bridge.get_pose()
    print(f"Final robot pose: x={final_pose[0]:.2f}, y={final_pose[1]:.2f}, yaw={final_pose[2]:.2f} rad")
    print("\n✅ Pure Pursuit Standalone Verification Passed Successfully!")
