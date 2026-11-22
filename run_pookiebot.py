"""
PookieBot Master Unified Application
====================================
Launches the complete PookieBot Physical AI ecosystem:
  1. HAL Motor & Sensor Bridge (Simulated MuJoCo or Real OpenBot Serial)
  2. Face WebSocket Bridge (Real-time animated eye display & Web Speech API)
  3. Vision Pipeline (Offscreen MuJoCo camera or live camera stream)
  4. Embodied Agent Brain (Tool calling, nursery routines, obstacle safety)

Controls:
  • Web Face: Speak into mic (🎙️ Speak) or click maneuver buttons!
  • 3D Viewer: [W][A][S][D] Drive, [Space] Stop, [1] Approach, [2] Dance, [3] Lullaby, [4] Patrol
  • Terminal: Type 'approach', 'dance', 'patrol', 'lullaby', 'forward', 'look', etc.
"""

import os
import sys
import time
import argparse
import webbrowser
import threading
import numpy as np

from core.hal import get_robot_bridge
from core.face_bridge import FaceBridgeServer
from core.vision import get_vision
from core.agent_brain import PookieBrain


def launch_sim_environment(model_path: str, with_gui: bool = False, face_server: FaceBridgeServer = None):
    """Initializes MuJoCo simulation, HAL bridge, and vision."""
    import mujoco
    import mujoco.viewer

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"MuJoCo model not found at {model_path}")

    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)

    bridge = get_robot_bridge(mode="sim", model=model, data=data)
    vision = get_vision(mode="sim", model=model, data=data)

    # In simulation without separate thread, step_sim advances physics
    def step_sim():
        bridge.step()
        mujoco.mj_step(model, data)

    brain = PookieBrain(bridge=bridge, face=face_server, vision=vision, step_sim_fn=step_sim if not with_gui else None)

    viewer_handle = None
    if with_gui:
        print("[PookieBot] Launching MuJoCo 3D Physics Viewer...")

        # Interactive 3D Viewer Keypress Callbacks
        def on_key(keycode):
            char = chr(keycode).upper() if 0 <= keycode < 256 else ""
            if char == "W":
                bridge.send_motors(160, 160)
            elif char == "S":
                bridge.send_motors(-160, -160)
            elif char == "A":
                bridge.send_motors(-130, 130)
            elif char == "D":
                bridge.send_motors(130, -130)
            elif keycode == 32:  # Space
                bridge.stop()
            elif char == "1":
                threading.Thread(target=brain.approach_object, daemon=True).start()
            elif char == "2":
                threading.Thread(target=brain.dance, daemon=True).start()
            elif char == "3":
                threading.Thread(target=brain.sing_lullaby, daemon=True).start()
            elif char == "4":
                threading.Thread(target=brain.patrol_nursery, daemon=True).start()

        viewer_handle = mujoco.viewer.launch_passive(model, data, key_callback=on_key)

    return model, data, bridge, vision, brain, viewer_handle


def run_automated_test():
    """Runs a complete end-to-end integration test of all modular components."""
    print("==================================================================")
    print("      POOKIEBOT END-TO-END MODULAR SIMULATION INTEGRATION TEST    ")
    print("==================================================================")

    model_path = os.path.join(os.path.dirname(__file__), "simulation", "models", "pookiebot.xml")

    # 1. Start Face Bridge
    print("\n[Step 1] Starting FaceBridge WebSocket Server on port 8765...")
    face_server = FaceBridgeServer(port=8765)
    face_server.start()
    time.sleep(0.3)
    print("  -> FaceBridge running!")

    # 2. Initialize Sim Environment
    print("\n[Step 2] Initializing MuJoCo HAL and Vision Pipeline...")
    model, data, bridge, vision, brain, _ = launch_sim_environment(model_path, with_gui=False, face_server=face_server)
    print("  -> HAL Bridge & Vision initialized cleanly!")

    # 3. Test Vision Capture
    print("\n[Step 3] Testing Offscreen Vision Capture...")
    frame = vision.capture_frame()
    assert frame is not None and frame.shape == (480, 640, 3), f"Invalid frame shape: {frame.shape}"
    heuristics = vision.analyze_scene_heuristics()
    print(f"  -> Vision OK! Scene heuristics: {heuristics}")

    # 4. Test Brain Natural Language Dispatcher & Emotions
    print("\n[Step 4] Testing Agent Brain & Emotional Transitions...")
    res = brain.execute_instruction("be happy and greet the baby")
    print(f"  -> Agent response: '{res}'")
    assert brain.current_emotion == "HAPPY", f"Expected HAPPY, got {brain.current_emotion}"

    # 5. Test Lullaby Nursery Routine
    print("\n[Step 5] Testing Lullaby Nursery Soothing Routine...")
    res = brain.execute_instruction("sing a lullaby for baby bedtime")
    print(f"  -> Agent response: '{res}'")
    assert brain.current_emotion == "LOVING", f"Expected LOVING, got {brain.current_emotion}"

    # 6. Test Approach Object Tool
    print("\n[Step 6] Testing Autonomous 'Approach Object' Tool...")
    import mujoco
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    res = brain.approach_object(stop_dist_m=0.22)
    sonar_dist = bridge.get_sonar_distance()
    pos = bridge.get_position()
    print(f"  -> {res}")
    print(f"  -> Robot Pos: X={pos[0]:.3f} m, Sonar: {sonar_dist*100:.1f} cm")
    assert sonar_dist <= 0.25 or bridge.is_safety_stop_active(), f"Failed to stop near object: {sonar_dist}"

    # 7. Test Celebratory Dance Maneuver
    print("\n[Step 7] Testing Celebratory Dance Maneuver...")
    res = brain.dance()
    print(f"  -> {res}")

    # 8. Test Visual Servoing to Named Target ("go to red cube")
    print("\n[Step 8] Testing Visual Servoing to Named Target ('red cube')...")
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)
    res = brain.execute_instruction("go to red cube")
    print(f"  -> {res}")
    assert "navigated to" in res.lower() or "approached" in res.lower(), f"Visual servoing failed: {res}"

    # 9. Test Pure Pursuit Trajectory Tracking
    print("\n[Step 9] Testing Pure Pursuit Trajectory Tracking...")
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)
    test_path = [(0.0, 0.0), (0.3, 0.15), (0.6, 0.25), (0.9, 0.15)]
    res = brain.follow_drawn_path(test_path)
    print(f"  -> {res}")
    assert "completed" in res.lower(), f"Pure pursuit failed: {res}"

    face_server.stop()
    print("\n==================================================================")
    print("  🎉 ALL MODULAR SIMULATION TESTS PASSED WITH 100% SUCCESS! 🚀   ")
    print("==================================================================")
    return True


def run_interactive_app(args):
    """Runs interactive master application with live control loop."""
    print("==================================================================")
    print("                   🧸 POOKIEBOT LIVING PHYSICAL AI                ")
    print("==================================================================")

    # 1. Start Face Bridge
    face_server = FaceBridgeServer(port=8765)
    face_server.start()

    # 2. Open Face in Web Browser if GUI requested
    if args.gui:
        face_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "web", "face.html"))
        print(f"[PookieBot] Opening Living Face in browser: file://{face_path}")
        webbrowser.open(f"file://{face_path}")

    # 3. Setup Hardware or Sim Environment
    if args.mode == "sim":
        model_path = os.path.join(os.path.dirname(__file__), "simulation", "models", "pookiebot.xml")
        model, data, bridge, vision, brain, viewer = launch_sim_environment(
            model_path, with_gui=args.gui, face_server=face_server
        )
    else:
        print(f"[PookieBot] Connecting to real hardware on {args.port}...")
        bridge = get_robot_bridge(mode="real", port=args.port)
        vision = get_vision(mode="real", source=0)
        brain = PookieBrain(bridge=bridge, face=face_server, vision=vision)
        viewer = None

    # Connect Browser Face (Voice / Buttons / Mini-Map Path) straight to the Brain
    face_server.on_command_callback = brain.execute_instruction
    face_server.on_path_callback = brain.follow_drawn_path

    print("\n[PookieBot] Controls Ready:")
    print("  🎙️  Voice: Click 'Speak' on the Web Face and speak into mic!")
    print("  🗺️  Mini-Map: Tap 'Map' to draw custom paths and send to Pure Pursuit follower!")
    print("  🔘  Targets: Tap '🟥 Cube', '🟡 Ball', '🟢 Bottle', '⚡ Dock' for visual servoing.")
    print("  💃  Maneuvers: 'Dance', 'Patrol', 'Lullaby', 'Scan Room'.")
    print("  🎮  3D Viewer: Focused window -> [W][A][S][D] to Drive, [Space] to Stop")
    print("  ⌨️   Terminal: Type 'go to red cube', 'circle', 'square', 'scan room', etc.")
    print("==================================================================\n")

    # Background viewer sync & telemetry broadcast thread
    stop_event = threading.Event()
    
    def telemetry_loop():
        """Periodically broadcast robot pose & telemetry to web face mini-map."""
        while not stop_event.is_set():
            try:
                face_server.broadcast_telemetry(bridge.get_telemetry())
            except Exception:
                pass
            time.sleep(0.06)  # ~16 Hz update rate

    tt = threading.Thread(target=telemetry_loop, daemon=True)
    tt.start()

    if viewer is not None:
        def viewer_loop():
            import mujoco
            while not stop_event.is_set() and viewer.is_running():
                step_start = time.time()
                bridge.step()
                mujoco.mj_step(model, data)
                viewer.sync()
                elapsed = time.time() - step_start
                dt = model.opt.timestep - elapsed
                if dt > 0:
                    time.sleep(dt)

        vt = threading.Thread(target=viewer_loop, daemon=True)
        vt.start()

    try:
        while True:
            cmd = input("PookieBot ❯ ")
            if not cmd or cmd.strip().lower() in ("exit", "quit", "q"):
                break
            reply = brain.execute_instruction(cmd)
            print(f"🤖 PookieBot: {reply}\n")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        print("\nShutting down PookieBot...")
        stop_event.set()
        bridge.stop()
        face_server.stop()
        print("Goodbye! 💖")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PookieBot Physical AI Companion")
    parser.add_argument("--mode", type=str, choices=["sim", "real"], default="sim", help="Run in MuJoCo sim or physical robot")
    parser.add_argument("--port", type=str, default="COM3", help="Serial port for real robot (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--gui", action="store_true", help="Launch 3D physics viewer and open browser face")
    parser.add_argument("--interactive", action="store_true", help="Interactive terminal command prompt")
    parser.add_argument("--test", action="store_true", help="Run full automated integration test suite")
    args = parser.parse_args()

    if args.test:
        run_automated_test()
    else:
        run_interactive_app(args)
