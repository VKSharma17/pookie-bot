"""
PookieBot Multimodal Vision-Language Model (VLM) Agent
======================================================
Connects simulated or physical camera frames to Gemini Multimodal models
(Gemini 2.5 / 2.0 / 1.5 Flash) for:
  1. Open-vocabulary nursery scene understanding.
  2. Grounded reasoning (detecting toys, baby crib, hazards).
  3. Structured Physical AI action planning (approaching targets, lullabies, patrols).
  4. Child-friendly emotional speech synthesis.

Includes an intelligent offline fallback utilizing local OpenCV heuristics and
TargetDetector when GEMINI_API_KEY is not configured.
"""

import os
import io
import json
import base64
from typing import Dict, Any, Optional, List
import numpy as np
import cv2

from .visual_servoing import TargetDetector, TargetType


class VLMAgent:
    """
    Multimodal scene reasoning agent connecting visual observations
    to high-level physical AI intentions and dialogue.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.detector = TargetDetector()
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print(f"[VLMAgent] Initialized Gemini VLM client with model '{model_name}'.")
            except Exception as e:
                print(f"[VLMAgent] Failed to initialize google-genai: {e}. Using local perception fallback.")

    def analyze_and_plan(self, frame_rgb: np.ndarray, user_prompt: str = "") -> Dict[str, Any]:
        """
        Analyze the current camera frame and return a structured plan:
          - scene_description: Human/child-friendly description of surroundings.
          - detected_objects: List of identified items.
          - recommended_action: Physical tool to call.
          - action_target: Target name if approaching.
          - spoken_response: What PookieBot says aloud.
          - emotion: Face expression to display.
        """
        if frame_rgb is None or frame_rgb.size == 0:
            return {
                "scene_description": "Camera feed unavailable.",
                "detected_objects": [],
                "recommended_action": "idle",
                "spoken_response": "I cannot see right now.",
                "emotion": "ALERT"
            }

        # If Gemini client is active, query cloud VLM
        if self.client:
            try:
                return self._query_gemini(frame_rgb, user_prompt)
            except Exception as e:
                print(f"[VLMAgent] Cloud VLM query failed ({e}). Falling back to local perception engine.")

        # Local intelligent perception fallback
        return self._local_perception_fallback(frame_rgb, user_prompt)

    def _query_gemini(self, frame_rgb: np.ndarray, user_prompt: str) -> Dict[str, Any]:
        """Query Gemini multimodal model with camera image and system prompt."""
        from google.genai import types

        # Encode RGB image to JPEG bytes
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        _, jpeg_buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_bytes = jpeg_buf.tobytes()

        system_instruction = (
            "You are PookieBot, a loving, cute, and intelligent home social robot companion "
            "for a baby and parents. You are observing the nursery room through your front camera.\n"
            "Analyze the image and respond with a strict, valid JSON object with these keys:\n"
            "{\n"
            '  "scene_description": "1-2 sentence warm description of what you see.",\n'
            '  "detected_objects": ["list", "of", "objects", "seen"],\n'
            '  "recommended_action": "approach" | "dance" | "lullaby" | "patrol" | "idle",\n'
            '  "action_target": "red cube" | "yellow ball" | "green bottle" | "dock" | null,\n'
            '  "spoken_response": "Cute, loving 1-sentence phrase to speak to baby/parent.",\n'
            '  "emotion": "HAPPY" | "CURIOUS" | "LOVING" | "SLEEPY" | "ALERT"\n'
            "}"
        )

        prompt = user_prompt or "What do you see in the nursery room, and what should we do next?"

        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt
        ]

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
                response_mime_type="application/json"
            )
        )

        return json.loads(response.text)

    def _local_perception_fallback(self, frame_rgb: np.ndarray, user_prompt: str) -> Dict[str, Any]:
        """
        Local deterministic visual reasoning engine using color segmentation,
        contour tracking, and ArUco landmark recognition.
        """
        detected = []
        target_in_view = None

        # Check each target in frame
        for t in [TargetType.RED_CUBE, TargetType.YELLOW_BALL, TargetType.GREEN_BOTTLE, TargetType.DOCKING_STATION]:
            res = self.detector.detect(frame_rgb, t)
            if res["found"]:
                name = t.value.replace("_", " ")
                err_x = res.get("error_x", 0.0)
                pos_str = "center" if abs(err_x) < 0.25 else ("right" if err_x > 0 else "left")
                detected.append(f"{name} ({pos_str})")
                if target_in_view is None:
                    target_in_view = name

        prompt_lower = user_prompt.lower()

        # Decide action and dialogue based on user prompt and detected targets
        if any(w in prompt_lower for w in ["sleep", "lullaby", "night", "cry", "soothe"]):
            return {
                "scene_description": f"I see the gentle nursery with {', '.join(detected) if detected else 'calm space'}.",
                "detected_objects": detected,
                "recommended_action": "lullaby",
                "action_target": None,
                "spoken_response": "Playing gentle music for baby bedtime. Shhh, sweet dreams! 💖",
                "emotion": "SLEEPY"
            }
        elif any(w in prompt_lower for w in ["dance", "party", "play", "celebrate"]):
            return {
                "scene_description": f"The play area is open and ready with {', '.join(detected) if detected else 'plenty of room'}!",
                "detected_objects": detected,
                "recommended_action": "dance",
                "action_target": None,
                "spoken_response": "Yay, let's dance together! Watch my robot spin! 💃",
                "emotion": "HAPPY"
            }
        elif target_in_view and any(w in prompt_lower for w in ["fetch", "get", "go to", "find", "cube", "ball", "bottle", "dock"]):
            return {
                "scene_description": f"I spot the {target_in_view} clearly ahead in the play area.",
                "detected_objects": detected,
                "recommended_action": "approach",
                "action_target": target_in_view,
                "spoken_response": f"I see the {target_in_view}! Driving over to inspect it now.",
                "emotion": "CURIOUS"
            }
        else:
            obj_str = ", ".join(detected) if detected else "a cozy, peaceful nursery"
            return {
                "scene_description": f"I am looking at {obj_str}.",
                "detected_objects": detected,
                "recommended_action": "idle",
                "action_target": target_in_view,
                "spoken_response": f"I see {obj_str}! What shall we play with?",
                "emotion": "HAPPY"
            }


# =====================================================================
# Standalone Unit Test
# =====================================================================
if __name__ == "__main__":
    import os
    import mujoco
    from core.vision import SimVision

    print("=== Testing PookieBot Multimodal VLM Agent ===")
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "simulation", "models", "pookiebot.xml")
    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    vision = SimVision(model, data, camera_name="robot_eye_camera")
    frame = vision.capture_frame()

    agent = VLMAgent()
    res = agent.analyze_and_plan(frame, "PookieBot, what toys are in front of you?")
    print("\nVLM Perception & Reasoning Output:")
    print(json.dumps(res, indent=2))

    assert "detected_objects" in res
    assert "recommended_action" in res
    assert "spoken_response" in res
    print("\n✅ VLM Agent Standalone Verification Passed Successfully!")
