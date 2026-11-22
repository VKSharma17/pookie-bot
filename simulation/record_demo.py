"""
PookieBot Video Showcase Recorder
=================================
Renders an offscreen MP4 video of PookieBot performing the approach
and celebratory dance in MuJoCo, saving it to disk for inspection.
"""

import os
import sys
import cv2
import numpy as np
import mujoco

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.hal import SimRobotBridge
from core.agent_brain import PookieBrain


def record_demo_video(output_mp4: str = "pookiebot_showcase.mp4", width: int = 1280, height: int = 720, fps: int = 30):
    model_path = os.path.join(os.path.dirname(__file__), "models", "pookiebot.xml")
    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)

    renderer = mujoco.Renderer(model, height=height, width=width)
    bridge = SimRobotBridge(model, data)
    from core.vision import SimVision
    vision = SimVision(model, data, camera_name="robot_eye_camera")

    frames = []

    def step_and_capture():
        mujoco.mj_step(model, data)
        # Capture at ~30 FPS (every 7 steps of 0.005s timestep)
        if len(frames) == 0 or data.time - len(frames) * (1.0 / fps) >= 0:
            renderer.update_scene(data, camera="third_person_view")
            rgb = renderer.render()
            frames.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

    brain = PookieBrain(bridge=bridge, vision=vision, step_sim_fn=step_and_capture)

    print("[VideoRecorder] Recording: Visual Servoing approach to Red Cube...")
    brain.navigate_to_target("red_cube", stop_dist_m=0.22)

    print("[VideoRecorder] Recording: Celebratory dance...")
    brain.dance()

    print("[VideoRecorder] Recording: Pure pursuit circular sweep...")
    brain.drive_circle(radius_m=0.5)

    # Save to MP4
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_mp4, fourcc, fps, (width, height))
    for f in frames:
        out.write(f)
    out.release()
    print(f"[VideoRecorder] Saved {len(frames)} frames to {output_mp4}! 🎥")


if __name__ == "__main__":
    record_demo_video()
