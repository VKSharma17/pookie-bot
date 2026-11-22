"""
PookieBot Hardware Abstraction Layer (HAL)
==========================================
Provides 100% plug-and-play Sim-to-Real parity.
Code written against BaseRobotBridge operates identically in:
  1. 'sim'  mode (MuJoCo 4.0 3D physics digital twin)
  2. 'real' mode (Physical OpenBot chassis via USB-OTG/Bluetooth serial)
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseRobotBridge(ABC):
    """Abstract interface defining all motor and sensor interactions."""

    def __init__(self, safety_stop_dist_m: float = 0.20):
        self.safety_dist = safety_stop_dist_m
        self.cmd_left_pwm = 0.0
        self.cmd_right_pwm = 0.0
        self.obstacle_stop_active = False
        self.latest_sonar_dist_m = 10.0
        self.battery_voltage = 7.4

    @abstractmethod
    def send_motors(self, left_pwm: float, right_pwm: float):
        """Send target motor PWM values in range [-255, 255]."""
        pass

    @abstractmethod
    def stop(self):
        """Instant emergency/active dynamic stop."""
        pass

    @abstractmethod
    def step(self) -> float:
        """Perform one control update step and return sonar distance in meters."""
        pass

    def get_sonar_distance(self) -> float:
        """Return the most recent obstacle distance in meters."""
        return self.latest_sonar_dist_m

    def is_safety_stop_active(self) -> bool:
        """Return True if hardware safety cutoff is currently engaged."""
        return self.obstacle_stop_active

    def get_telemetry(self) -> Dict[str, Any]:
        """Return a snapshot of current telemetry data."""
        return {
            "cmd_left": self.cmd_left_pwm,
            "cmd_right": self.cmd_right_pwm,
            "sonar_m": self.latest_sonar_dist_m,
            "safety_stop": self.obstacle_stop_active,
            "battery_v": self.battery_voltage
        }


class SimRobotBridge(BaseRobotBridge):
    """
    Simulation implementation of BaseRobotBridge using MuJoCo physics.
    Controls actuators and reads rangefinder sensor directly from MjModel & MjData.
    """

    def __init__(self, model, data, max_speed_rad_s: float = 12.0, safety_stop_dist_m: float = 0.20):
        super().__init__(safety_stop_dist_m=safety_stop_dist_m)
        import mujoco
        self.mujoco = mujoco
        self.model = model
        self.data = data
        self.max_speed = max_speed_rad_s

        # Look up actuator and sensor IDs
        self.sensor_sonar_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "ultrasonic_sonar")
        self.act_fl = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_fl")
        self.act_rl = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_rl")
        self.act_fr = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_fr")
        self.act_rr = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "act_rr")
        self.body_robot_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "pookiebot")

        # Smooth velocity ramping states
        self.cur_left = 0.0
        self.cur_right = 0.0

    def send_motors(self, left_pwm: float, right_pwm: float):
        """Clamp and store desired motor PWM."""
        self.cmd_left_pwm = max(-255.0, min(255.0, float(left_pwm)))
        self.cmd_right_pwm = max(-255.0, min(255.0, float(right_pwm)))

    def stop(self):
        """Zero out commanded velocities."""
        self.cmd_left_pwm = 0.0
        self.cmd_right_pwm = 0.0

    def step(self) -> float:
        """Read sensor, check safety threshold, and write actuator controls."""
        # 1. Read ultrasonic sensor
        sonar_dist = 10.0
        if self.sensor_sonar_id != -1:
            sensor_adr = self.model.sensor_adr[self.sensor_sonar_id]
            val = float(self.data.sensordata[sensor_adr])
            if val > 0.02:
                sonar_dist = val
            else:
                sonar_dist = 10.0
        self.latest_sonar_dist_m = sonar_dist

        # 2. Hardware-level obstacle fail-safe
        is_moving_forward = (self.cmd_left_pwm > 0) or (self.cmd_right_pwm > 0)
        if sonar_dist <= self.safety_dist and is_moving_forward:
            self.obstacle_stop_active = True
            target_left = 0.0
            target_right = 0.0
        else:
            self.obstacle_stop_active = False
            target_left = (self.cmd_left_pwm / 255.0) * self.max_speed
            target_right = (self.cmd_right_pwm / 255.0) * self.max_speed

        # Smooth velocity ramping (prevents physical shock / tipping)
        ramp_rate = 0.8
        self.cur_left += max(-ramp_rate, min(ramp_rate, target_left - self.cur_left))
        self.cur_right += max(-ramp_rate, min(ramp_rate, target_right - self.cur_right))

        # 3. Apply to wheel actuators
        self.data.ctrl[self.act_fl] = self.cur_left
        self.data.ctrl[self.act_rl] = self.cur_left
        self.data.ctrl[self.act_fr] = self.cur_right
        self.data.ctrl[self.act_rr] = self.cur_right

        return sonar_dist

    def get_position(self):
        """Return 3D global position [x, y, z] of the robot body in simulation."""
        return self.data.xpos[self.body_robot_id].copy()


class RealRobotBridge(BaseRobotBridge):
    """
    Physical hardware implementation of BaseRobotBridge.
    Communicates with Arduino Nano via USB-OTG Serial using OpenBot protocol (115200 baud).
    """

    def __init__(self, port: str = "COM3", baudrate: int = 115200, safety_stop_dist_m: float = 0.20):
        super().__init__(safety_stop_dist_m=safety_stop_dist_m)
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_connected = False
        self._rx_thread = None
        self._running = False

        self._connect_serial()

    def _connect_serial(self):
        """Attempt to open physical serial connection."""
        try:
            import serial
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=0.1)
            self.is_connected = True
            self._running = True
            self._rx_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._rx_thread.start()
            print(f"[RealRobotBridge] Connected to physical Arduino on {self.port} at {self.baudrate} baud.")
        except Exception as e:
            print(f"[RealRobotBridge] Warning: Could not open {self.port} ({e}). Operating in dry-run mode.")
            self.is_connected = False

    def _read_loop(self):
        """Background thread parsing incoming OpenBot telemetry strings."""
        buffer = ""
        while self._running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                # Parse OpenBot protocol:
                # 's<dist>' -> Sonar distance in cm
                if line.startswith('s'):
                    dist_cm = float(line[1:])
                    self.latest_sonar_dist_m = dist_cm / 100.0
                    if self.latest_sonar_dist_m <= self.safety_dist and (self.cmd_left_pwm > 0 or self.cmd_right_pwm > 0):
                        self.obstacle_stop_active = True
                    else:
                        self.obstacle_stop_active = False
                # 'v<volts>' -> Battery voltage
                elif line.startswith('v'):
                    self.battery_voltage = float(line[1:])
            except Exception:
                pass

    def send_motors(self, left_pwm: float, right_pwm: float):
        """Format command as 'c<left>,<right>\n' and write to serial."""
        self.cmd_left_pwm = max(-255.0, min(255.0, float(left_pwm)))
        self.cmd_right_pwm = max(-255.0, min(255.0, float(right_pwm)))

        # Hardware safety check
        if self.obstacle_stop_active and (self.cmd_left_pwm > 0 or self.cmd_right_pwm > 0):
            payload = "c0,0\n"
        else:
            payload = f"c{int(self.cmd_left_pwm)},{int(self.cmd_right_pwm)}\n"

        if self.is_connected and self.serial_conn:
            try:
                self.serial_conn.write(payload.encode('ascii'))
            except Exception as e:
                print(f"[RealRobotBridge] Serial write error: {e}")

    def stop(self):
        """Send immediate stop packet."""
        self.send_motors(0, 0)

    def step(self) -> float:
        """In real hardware, updates happen asynchronously in background thread."""
        return self.latest_sonar_dist_m

    def close(self):
        """Clean shutdown."""
        self.stop()
        self._running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()


def get_robot_bridge(mode: str = "sim", **kwargs) -> BaseRobotBridge:
    """
    Factory function for seamless Sim-to-Real switching.
    Usage:
        bridge = get_robot_bridge(mode="sim", model=m, data=d)
        # or for real hardware:
        bridge = get_robot_bridge(mode="real", port="COM3")
    """
    if mode.lower() == "sim":
        model = kwargs.get("model")
        data = kwargs.get("data")
        if model is None or data is None:
            raise ValueError("SimRobotBridge requires 'model' and 'data' arguments.")
        return SimRobotBridge(model=model, data=data, **{k: v for k, v in kwargs.items() if k not in ("model", "data")})
    elif mode.lower() == "real":
        return RealRobotBridge(**kwargs)
    else:
        raise ValueError(f"Unknown bridge mode: '{mode}'. Must be 'sim' or 'real'.")
