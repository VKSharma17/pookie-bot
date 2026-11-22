"""
PookieBot Embodied Physical AI Brain
===================================
Orchestrates the cognitive loop:
  1. Multimodal Perception (Vision + Audio + Sonar)
  2. Embodied Tool Calling (drive, turn, express, inspect, sing, dance, approach)
  3. Emotional State Transitions & Nursery Guardrails
"""

import time
import math
from typing import Optional, Dict, Any, List, Tuple
from .hal import BaseRobotBridge
from .face_bridge import FaceBridgeServer
from .vision import BaseVision
from .visual_servoing import VisualServoingController, TargetDetector, TargetType
from .path_follower import PurePursuitController
from .vlm_agent import VLMAgent


class PookieBrain:
    """The central cognitive mind orchestrating body, face, and perception."""

    def __init__(
        self,
        bridge: BaseRobotBridge,
        face: Optional[FaceBridgeServer] = None,
        vision: Optional[BaseVision] = None,
        step_sim_fn: Optional[Any] = None
    ):
        self.bridge = bridge
        self.face = face
        self.vision = vision
        self.step_sim_fn = step_sim_fn

        self.state = "IDLE"
        self.current_emotion = "NEUTRAL"
        self.is_patrolling = False

        # Spatial Navigation & Control Modules
        self.detector = TargetDetector()
        self.vlm = VLMAgent()
        self.servoing = None
        if self.vision:
            self.servoing = VisualServoingController(
                bridge=self.bridge,
                vision=self.vision,
                step_sim_fn=self.step_sim_fn
            )
        self.pursuit = PurePursuitController(
            bridge=self.bridge,
            step_sim_fn=self.step_sim_fn
        )

    def _face_callback(self, emotion: str, msg: str):
        """Update face expression and speech output."""
        self.express(emotion)
        if self.face:
            self.face.send_response(msg)

    def _sleep_or_step(self, duration_s: float):
        """Wait for duration, properly paced to simulation timestep."""
        dt = 0.005
        steps = max(1, int(duration_s / dt))
        if callable(self.step_sim_fn):
            for _ in range(steps):
                self.bridge.step()
                self.step_sim_fn()
        else:
            time.sleep(duration_s)

    # =========================================================================
    # Physical AI Embodied Tool Calling
    # =========================================================================

    def express(self, emotion: str, sound: Optional[str] = None):
        """Tool: Change facial expression and play emotive audio cue."""
        emotion = emotion.upper()
        self.current_emotion = emotion
        if self.face:
            self.face.set_emotion(emotion)
            sound_type = sound or emotion.lower()
            self.face.play_sound(sound_type)
        print(f"[PookieBrain Tool] express('{emotion}', sound='{sound or emotion.lower()}')")

    def drive(self, direction: str = "forward", speed_pwm: int = 140, duration_s: float = 1.0) -> bool:
        """
        Tool: Move the robot safely forward or backward.
        Monitors ultrasonic distance during every control tick.
        Returns True if motion completed, False if aborted by obstacle.
        """
        print(f"[PookieBrain Tool] drive(direction='{direction}', pwm={speed_pwm}, duration={duration_s}s)")
        direction = direction.lower()
        pwm = abs(speed_pwm) if direction == "forward" else -abs(speed_pwm)

        if self.face:
            self.face.set_emotion("HAPPY" if direction == "forward" else "CURIOUS")

        dt = 0.005
        steps = max(1, int(duration_s / dt))
        self.bridge.send_motors(pwm, pwm)

        success = True
        for _ in range(steps):
            sonar_dist = self.bridge.step()
            if callable(self.step_sim_fn):
                self.step_sim_fn()
            else:
                time.sleep(dt)

            # Safety stop check
            if self.bridge.is_safety_stop_active():
                print(f"[PookieBrain Safety] Obstacle detected at {sonar_dist*100:.1f} cm! Halting immediately.")
                self.bridge.stop()
                self.express("ALERT", "curious")
                if self.face:
                    self.face.look_at(0, -15)
                success = False
                break

        self.bridge.stop()
        if callable(self.step_sim_fn):
            self.step_sim_fn()

        return success

    def turn(self, direction: str = "left", angle_deg: float = 45, speed_pwm: int = 120):
        """Tool: Rotate the robot on the spot."""
        print(f"[PookieBrain Tool] turn(direction='{direction}', angle={angle_deg} deg)")
        direction = direction.lower()
        turn_duration = (angle_deg / 90.0) * 0.45

        if direction == "left":
            self.bridge.send_motors(-speed_pwm, speed_pwm)
            if self.face:
                self.face.look_at(-25, 0)
        else:
            self.bridge.send_motors(speed_pwm, -speed_pwm)
            if self.face:
                self.face.look_at(25, 0)

        self._sleep_or_step(turn_duration)
        self.bridge.stop()
        if self.face:
            self.face.look_at(0, 0)

    def approach_object(self, stop_dist_m: float = 0.22) -> str:
        """
        Tool: Autonomously drive towards the object in front,
        decelerating smoothly and halting precisely right in front of it!
        """
        print(f"[PookieBrain Tool] approach_object() -> driving towards obstacle until {stop_dist_m*100:.0f}cm")
        self.express("CURIOUS", "curious")
        if self.face:
            self.face.look_at(0, 10)

        dt = 0.005
        max_steps = int(8.0 / dt)

        for step_idx in range(max_steps):
            sonar_dist = self.bridge.step()
            if callable(self.step_sim_fn):
                self.step_sim_fn()
            else:
                time.sleep(dt)

            if step_idx % 20 == 0:
                print(f"\r  Approaching... Distance: {sonar_dist*100:.1f} cm", end="", flush=True)

            if sonar_dist <= stop_dist_m or self.bridge.is_safety_stop_active():
                print(f"\n[PookieBrain] Arrived at object! Distance: {sonar_dist*100:.1f} cm.")
                self.bridge.stop()
                self.express("HAPPY", "happy")
                if self.face:
                    self.face.look_at(0, -10)
                if self.vision:
                    self.inspect_scene()
                return f"Arrived right in front of object ({sonar_dist*100:.1f} cm away) and inspected it!"

            # Dynamic speed tapering
            if sonar_dist > 0.45:
                pwm = 140
            else:
                pwm = 100
            self.bridge.send_motors(pwm, pwm)

        self.bridge.stop()
        print("\n[PookieBrain] Approach search timeout reached.")
        return "Approached as far as possible."

    def dance(self):
        """Tool: A cute, joyful celebratory dance routine!"""
        print("[PookieBrain Tool] dance() - Performing happy robot dance! 💃")
        self.express("HAPPY", "happy")

        # 1. Spin left 360 degrees
        self.bridge.send_motors(-150, 150)
        self._sleep_or_step(0.9)
        self.bridge.stop()
        self._sleep_or_step(0.1)

        # 2. Spin right 360 degrees
        self.express("LOVING", "love")
        self.bridge.send_motors(150, -150)
        self._sleep_or_step(0.9)
        self.bridge.stop()
        self._sleep_or_step(0.1)

        # 3. Wiggle forward/back
        for _ in range(2):
            self.bridge.send_motors(140, 140)
            self._sleep_or_step(0.2)
            self.bridge.send_motors(-140, -140)
            self._sleep_or_step(0.2)

        self.bridge.stop()
        self.express("HAPPY", "happy")
        print("[PookieBrain] Dance complete! 💖")
        return "I did my happy dance for you and baby!"

    def figure_eight(self):
        """Tool: Drive in a smooth figure-8 loop."""
        print("[PookieBrain Tool] figure_eight() - Executing figure-8 path")
        self.express("HAPPY", "curious")

        # First loop (turn left while moving forward)
        self.bridge.send_motors(80, 150)
        self._sleep_or_step(2.2)

        # Second loop (turn right while moving forward)
        self.bridge.send_motors(150, 80)
        self._sleep_or_step(2.2)

        self.bridge.stop()
        self.express("HAPPY", "happy")
        return "Completed figure-8 maneuver!"

    def inspect_scene(self) -> Dict[str, Any]:
        """Tool: Capture visual camera frame and analyze scene properties."""
        print("\n[PookieBrain Tool] inspect_scene()")
        self.express("CURIOUS", "curious")
        if self.face:
            self.face.blink()

        if not self.vision:
            return {"status": "no_vision_module"}

        heuristics = self.vision.analyze_scene_heuristics()
        sonar_m = self.bridge.get_sonar_distance()
        heuristics["obstacle_distance_cm"] = round(sonar_m * 100, 1)

        print(f"[PookieBrain Perception] Scene analysis: {heuristics}")
        return heuristics

    def sing_lullaby(self, song: str = "brahms"):
        """Tool: Enter gentle nursery soothing routine for the baby."""
        print(f"[PookieBrain Tool] sing_lullaby('{song}') - Nursery soothing mode active")
        self.express("SLEEPY", "sleepy")
        self.bridge.stop()

        # Gentle side-to-side slow sway (mimicking rocking a cradle)
        for _ in range(2):
            self.turn("left", angle_deg=12, speed_pwm=70)
            self._sleep_or_step(0.15)
            self.turn("right", angle_deg=24, speed_pwm=70)
            self._sleep_or_step(0.15)
            self.turn("left", angle_deg=12, speed_pwm=70)

        self.express("LOVING", "love")
        return "Playing soothing lullaby mode for bedtime."

    def patrol_nursery(self, cycles: int = 3):
        """Tool: Autonomous nursery check avoiding obstacles gently."""
        print(f"[PookieBrain Tool] patrol_nursery(cycles={cycles})")
        self.is_patrolling = True
        self.express("CURIOUS", "curious")

        for cycle in range(cycles):
            print(f"\n--- Patrol Cycle {cycle+1}/{cycles} ---")
            # 1. Drive forward gently
            success = self.drive("forward", speed_pwm=130, duration_s=1.2)

            # 2. Inspect surroundings
            scene = self.inspect_scene()

            # 3. Pivot if blocked or to explore next corner
            if not success:
                print("Path blocked! Reversing and selecting open angle.")
                self.drive("backward", speed_pwm=110, duration_s=0.5)
                self.turn("right", angle_deg=75)
            else:
                self.turn("left", angle_deg=50)

        self.is_patrolling = False
        self.express("HAPPY", "happy")
        print("[PookieBrain Tool] Nursery patrol complete. Baby area is safe! 💖")
        return "Completed nursery patrol. All clear and safe!"

    def navigate_to_target(self, target_name: str, stop_dist_m: float = 0.22) -> str:
        """Tool: Closed-loop visual servoing to center and approach a named target."""
        print(f"\n[PookieBrain Tool] navigate_to_target('{target_name}', stop_dist={stop_dist_m}m)")
        if not self.servoing:
            return "Visual servoing module is not enabled (requires vision camera)."

        res = self.servoing.navigate_to_target(
            target_name=target_name,
            stop_dist_m=stop_dist_m,
            face_callback=self._face_callback
        )
        if res["success"]:
            self.express("LOVING", "happy")
            return f"Successfully navigated to {res['target']}! Stopped at {res.get('final_sonar_m', 0.22)*100:.1f} cm."
        else:
            self.express("ALERT", "curious")
            return f"Navigation to {target_name} incomplete: {res.get('reason', 'target not reached')}."

    def follow_drawn_path(self, waypoints: List[Tuple[float, float]]) -> str:
        """Tool: Pure Pursuit path tracking along 2D coordinates drawn on UI mini-map."""
        print(f"\n[PookieBrain Tool] follow_drawn_path({len(waypoints)} waypoints)")
        res = self.pursuit.follow_path(
            waypoints=waypoints,
            face_callback=self._face_callback
        )
        if res["success"]:
            self.express("HAPPY", "happy")
            return f"Successfully completed custom drawn trajectory in {res.get('steps', 0)} steps!"
        else:
            self.express("ALERT", "curious")
            return f"Trajectory stopped: {res.get('reason')}."

    def drive_circle(self, radius_m: float = 0.6) -> str:
        """Tool: Execute a smooth circular trajectory."""
        print(f"\n[PookieBrain Tool] drive_circle(radius={radius_m}m)")
        curr_x, curr_y, _ = self.bridge.get_pose()
        # Generate 16 circular waypoints
        waypoints = []
        for i in range(17):
            angle = i * (2.0 * math.pi / 16.0)
            wx = curr_x + radius_m * math.sin(angle)
            wy = curr_y + radius_m * (1.0 - math.cos(angle))
            waypoints.append((round(wx, 3), round(wy, 3)))
        return self.follow_drawn_path(waypoints)

    def drive_square(self, side_m: float = 0.7) -> str:
        """Tool: Execute a geometric square patrol."""
        print(f"\n[PookieBrain Tool] drive_square(side={side_m}m)")
        curr_x, curr_y, _ = self.bridge.get_pose()
        waypoints = [
            (round(curr_x, 3), round(curr_y, 3)),
            (round(curr_x + side_m, 3), round(curr_y, 3)),
            (round(curr_x + side_m, 3), round(curr_y + side_m, 3)),
            (round(curr_x, 3), round(curr_y + side_m, 3)),
            (round(curr_x, 3), round(curr_y, 3)),
        ]
        return self.follow_drawn_path(waypoints)

    def scan_room(self) -> str:
        """Tool: 360-degree sweep detecting and logging all recognizable objects."""
        print("\n[PookieBrain Tool] scan_room()")
        self.express("CURIOUS", "curious")
        if not self.vision:
            return "Vision module required to scan room."

        found_targets = []
        for _ in range(12):
            self.turn("left", angle_deg=30, speed_pwm=100)
            frame = self.vision.capture_frame()
            for t in [TargetType.RED_CUBE, TargetType.YELLOW_BALL, TargetType.GREEN_BOTTLE, TargetType.DOCKING_STATION]:
                det = self.detector.detect(frame, t)
                if det["found"] and t.value not in found_targets:
                    found_targets.append(t.value)

        self.express("HAPPY", "happy")
        report = f"Scan complete! Identified: {', '.join(found_targets) if found_targets else 'no clear landmarks'}."
        print(f"[PookieBrain Report] {report}")
        return report

    # =========================================================================
    # Natural Language Command Dispatcher
    # =========================================================================

    def execute_instruction(self, text: str) -> str:
        """
        Interprets natural language voice/text commands and triggers physical AI tools.
        Acts as the embodied agent's cognitive dispatcher.
        """
        text = text.lower().strip()
        print(f"\n[PookieBrain] 🎙️ Processing command: '{text}'")

        # Check for named target objects first ("go to red cube", "find yellow ball", "dock")
        target_type = TargetDetector.resolve_target(text)
        if target_type is not None and any(verb in text for verb in ["go", "find", "reach", "approach", "drive to", "navigate", "to", "target", "dock"]):
            return self.navigate_to_target(target_type.value)

        if any(w in text for w in ["circle", "drive in a circle", "spin circle"]):
            return self.drive_circle()

        elif any(w in text for w in ["square", "box pattern", "patrol square"]):
            return self.drive_square()

        elif any(w in text for w in ["scan room", "survey room", "look around room", "find toys"]):
            return self.scan_room()

        elif any(w in text for w in ["dance", "celebrate", "spin", "party"]):
            return self.dance()

        elif any(w in text for w in ["approach", "go to object", "come close", "near"]):
            return self.approach_object()

        elif any(w in text for w in ["figure eight", "figure 8"]):
            return self.figure_eight()

        elif any(w in text for w in ["happy", "smile", "greet", "hello", "hi"]):
            self.express("HAPPY", "happy")
            return "I'm smiling and happy to see you and baby!"

        elif any(w in text for w in ["love", "loving", "cute", "kiss", "sweet"]):
            self.express("LOVING", "love")
            return "Sending gentle love to baby! 💖"

        elif any(w in text for w in ["sleep", "lullaby", "night", "soothe", "bedtime"]):
            return self.sing_lullaby("brahms")

        elif any(w in text for w in ["patrol", "guard", "scan", "explore", "check room"]):
            return self.patrol_nursery(cycles=2)

        elif any(w in text for w in ["forward", "come here", "drive", "move"]):
            ok = self.drive("forward", speed_pwm=140, duration_s=1.2)
            return "Moved forward." if ok else "Stopped due to nearby obstacle."

        elif any(w in text for w in ["backward", "back up", "reverse"]):
            self.drive("backward", speed_pwm=130, duration_s=1.0)
            return "Backed up gently."

        elif any(w in text for w in ["turn left", "left"]):
            self.turn("left", angle_deg=45)
            return "Turned left."

        elif any(w in text for w in ["turn right", "right"]):
            self.turn("right", angle_deg=45)
            return "Turned right."

        elif any(w in text for w in ["look", "see", "inspect", "camera", "what do you see", "describe"]):
            if self.vision:
                frame = self.vision.capture_frame()
                plan = self.vlm.analyze_and_plan(frame, user_prompt=text)
                self.express(plan.get("emotion", "HAPPY"))
                spoken = plan.get("spoken_response", plan.get("scene_description", "All clear!"))
                if self.face:
                    self.face.send_response(spoken)
                if plan.get("recommended_action") == "approach" and plan.get("action_target"):
                    self.navigate_to_target(plan["action_target"])
                return spoken
            analysis = self.inspect_scene()
            dist = analysis.get("obstacle_distance_cm", "clear")
            return f"I see the nursery area. Forward obstacle distance is {dist} cm."

        elif any(w in text for w in ["stop", "halt", "stay", "freeze"]):
            self.bridge.stop()
            self.express("NEUTRAL")
            return "Halted."

        else:
            self.express("CURIOUS", "curious")
            return f"I'm listening! (Understood: '{text}')"
