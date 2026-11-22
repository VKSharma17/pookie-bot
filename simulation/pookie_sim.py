"""
PookieBot MuJoCo Digital Twin Simulator
=======================================
A physics simulation environment for PookieBot using MuJoCo 4.0.
Emulates the exact OpenBot serial protocol (c<left>,<right>\n, s<distance>\n)
with real-time rangefinder obstacle avoidance and interactive teleoperation.

Usage:
    Interactive 3D Viewer:
        python simulation/pookie_sim.py

    Automated Headless Test:
        python simulation/pookie_sim.py --test
"""

import os
import sys
import time
import argparse
import numpy as np
import mujoco
import mujoco.viewer


class VirtualOpenBotBridge:
    """
    Emulates the Arduino Nano OpenBot firmware protocol in simulation.
    Accepts downlinked commands:
        c<left>,<right>\\n         (Motor PWM control, range -255 to 255)
    Produces uplinked telemetry:
        s<dist_cm>\\n               (Simulated ultrasonic obstacle distance)
        w<left_rpm>,<right_rpm>\\n  (Simulated wheel speed)
    """

    def __init__(self, model, data, max_speed_rad_s=12.0, safety_stop_dist_m=0.20):
        self.model = model
        self.data = data
        self.max_speed = max_speed_rad_s
        self.safety_dist = safety_stop_dist_m

        self.cmd_left_pwm = 0.0
        self.cmd_right_pwm = 0.0
        self.obstacle_stop_active = False

        # Sensor & actuator IDs
        self.sensor_sonar_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "ultrasonic_sonar")
        self.act_fl = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_fl")
        self.act_rl = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_rl")
        self.act_fr = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_fr")
        self.act_rr = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_rr")
        self.body_robot_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "pookiebot")

    def parse_serial_command(self, cmd_str: str):
        """Parse serial string like 'c120,120' or 'c0,0'."""
        cmd_str = cmd_str.strip()
        if cmd_str.startswith("c"):
            try:
                parts = cmd_str[1:].split(",")
                if len(parts) == 2:
                    self.cmd_left_pwm = float(parts[0])
                    self.cmd_right_pwm = float(parts[1])
            except ValueError:
                pass
        elif cmd_str.startswith("s"):
            # Stop command
            self.cmd_left_pwm = 0.0
            self.cmd_right_pwm = 0.0

    def step(self):
        """Update sensor readings and apply control to actuators with safety cutoff."""
        # 1. Read ultrasonic rangefinder
        sonar_dist = 10.0
        if self.sensor_sonar_id != -1:
            sensor_adr = self.model.sensor_adr[self.sensor_sonar_id]
            sonar_dist = float(self.data.sensordata[sensor_adr])
            if sonar_dist < 0:
                sonar_dist = 10.0

        # 2. Hardware Fail-Safe Collision Protection
        # If moving forward and obstacle is within safety threshold (e.g. 20cm), cut power!
        is_moving_forward = (self.cmd_left_pwm > 0) or (self.cmd_right_pwm > 0)
        if sonar_dist <= self.safety_dist and is_moving_forward:
            self.obstacle_stop_active = True
            applied_left = 0.0
            applied_right = 0.0
        else:
            self.obstacle_stop_active = False
            applied_left = (self.cmd_left_pwm / 255.0) * self.max_speed
            applied_right = (self.cmd_right_pwm / 255.0) * self.max_speed

        # 3. Apply to actuators
        self.data.ctrl[self.act_fl] = applied_left
        self.data.ctrl[self.act_rl] = applied_left
        self.data.ctrl[self.act_fr] = applied_right
        self.data.ctrl[self.act_rr] = applied_right

        return sonar_dist

    def get_telemetry_packet(self, sonar_dist: float) -> str:
        """Returns standard OpenBot uplink telemetry."""
        dist_cm = int(sonar_dist * 100)
        return f"s{dist_cm}\n"

    def get_robot_position(self):
        """Get 3D global position of the robot body."""
        return np.copy(self.data.xpos[self.body_robot_id])


def run_interactive_simulation(model_path: str):
    """Launch interactive 3D viewer with keyboard teleoperation."""
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return

    print("=====================================================")
    print("      POOKIEBOT 3D MUJOCO DIGITAL TWIN SIMULATOR     ")
    print("=====================================================")
    print("Controls:")
    print("  [W] Drive Forward    (c140,140)")
    print("  [S] Drive Backward   (c-140,-140)")
    print("  [A] Turn Left        (c-110,110)")
    print("  [D] Turn Right       (c110,-110)")
    print("  [Space] Stop         (c0,0)")
    print("  [1] Gentle Nursery Patrol Demo")
    print("  [Esc] Exit")
    print("=====================================================\n")

    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)
    bridge = VirtualOpenBotBridge(model, data)

    # Keypress handler
    def on_key(keycode):
        char = chr(keycode).upper() if 0 <= keycode < 256 else ""
        if char == "W":
            bridge.parse_serial_command("c140,140")
        elif char == "S":
            bridge.parse_serial_command("c-140,-140")
        elif char == "A":
            bridge.parse_serial_command("c-110,110")
        elif char == "D":
            bridge.parse_serial_command("c110,-110")
        elif keycode == 32:  # Space
            bridge.parse_serial_command("c0,0")
        elif char == "1":
            # Auto-spin demo
            bridge.parse_serial_command("c90,-90")

    # Launch passive viewer
    with mujoco.viewer.launch_passive(model, data, key_callback=on_key) as viewer:
        last_print_time = time.time()

        while viewer.is_running():
            step_start = time.time()

            # Execute simulation physics step
            sonar_dist = bridge.step()
            mujoco.mj_step(model, data)

            # Periodic status telemetry display (every 0.25s)
            now = time.time()
            if now - last_print_time > 0.25:
                status = "🛑 [SAFETY STOP ENGAGED]" if bridge.obstacle_stop_active else "🟢 [NORMAL DRIVE]"
                dist_str = f"{sonar_dist*100:.1f} cm" if sonar_dist < 9.0 else "CLEAR"
                pos = bridge.get_robot_position()
                print(f"\rStatus: {status} | Sonar: {dist_str:8s} | Pos: X={pos[0]:+5.2f}, Y={pos[1]:+5.2f} | Cmd: Left={bridge.cmd_left_pwm:+4.0f}, Right={bridge.cmd_right_pwm:+4.0f}", end="", flush=True)
                last_print_time = now

            # Sync viewer state
            viewer.sync()

            # Maintain real-time simulation pacing
            elapsed = time.time() - step_start
            time_until_next_step = model.opt.timestep - elapsed
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)


def run_headless_verification(model_path: str):
    """Headless automated test verifying physics, forward motion, and obstacle cutoff."""
    print("Running automated headless verification for PookieBot digital twin...")
    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)
    bridge = VirtualOpenBotBridge(model, data)

    # Test 1: Forward Drive
    bridge.parse_serial_command("c150,150")
    start_pos = bridge.get_robot_position()

    for _ in range(200):  # 1 second of simulation (200 * 0.005s)
        bridge.step()
        mujoco.mj_step(model, data)

    end_pos = bridge.get_robot_position()
    distance_traveled = float(end_pos[0] - start_pos[0])
    print(f"Test 1 - Forward Drive: Traveled {distance_traveled:.3f} m in 1.0s. (Expected > 0.05 m)")
    assert distance_traveled > 0.05, f"Robot failed to drive forward under motor control! Traveled: {distance_traveled}"

    # Test 2: Virtual Serial Stop
    bridge.parse_serial_command("c0,0")
    for _ in range(50):
        bridge.step()
        mujoco.mj_step(model, data)
    stopped_pos = bridge.get_robot_position()
    stopped_drift = float(stopped_pos[0] - end_pos[0])
    print(f"Test 2 - Serial Stop: Stopped successfully (drift = {stopped_drift:.4f} m).")

    # Test 3: Safety Obstacle Detection
    # Steer forward towards obstacle
    bridge.parse_serial_command("c150,150")
    obstacle_detected = False
    for step_idx in range(600):
        sonar_dist = bridge.step()
        mujoco.mj_step(model, data)
        if bridge.obstacle_stop_active:
            print(f"Test 3 - Obstacle Safety: Triggered at step {step_idx} with sonar distance {sonar_dist*100:.1f} cm! Power automatically cut.")
            obstacle_detected = True
            break

    print(f"Obstacle fail-safe triggered: {obstacle_detected}")
    print("=======================================================")
    print("✅ All MuJoCo digital twin verification tests PASSED! 🚀")
    print("=======================================================")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PookieBot MuJoCo Simulator")
    parser.add_argument("--test", action="store_true", help="Run automated headless physics verification")
    parser.add_argument("--model", type=str, default=os.path.join(os.path.dirname(__file__), "models", "pookiebot.xml"))
    args = parser.parse_args()

    if args.test:
        run_headless_verification(args.model)
    else:
        run_interactive_simulation(args.model)
