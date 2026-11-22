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
from typing import Optional, Dict, Any, List
from .hal import BaseRobotBridge
from .face_bridge import FaceBridgeServer
from .vision import BaseVision


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

        if any(w in text for w in ["dance", "celebrate", "spin", "party"]):
            return self.dance()

        elif any(w in text for w in ["approach", "go to object", "come close", "near"]):
            return self.approach_object()

        elif any(w in text for w in ["figure eight", "figure 8", "circle"]):
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

        elif any(w in text for w in ["look", "see", "inspect", "camera", "what do you see"]):
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
