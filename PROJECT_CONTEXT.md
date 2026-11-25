# 🧸 PookieBot: Complete Project State & Context Dossier

> **Single Source of Truth for Antigravity Projects**  
> **Project Directory**: `d:\VKS\SelfMade\PookieBot`  
> **Git Repository**: [https://github.com/VKSharma17/pookie-bot](https://github.com/VKSharma17/pookie-bot) (`main` branch)  
> **Last Updated**: November 25, 2026  
> **Dedication**: A DIY modern Physical AI mobile social robot companion for a newborn baby girl (1 month old).

---

## 1. Executive Summary & Purpose

PookieBot is a practical, DIY, low-cost Physical AI social robot embodiment created to explore modern Physical AI, Human-Robot Interaction (HRI), and embodied intelligence.

### The Problem It Solves
Most social robots (Anki Vector, Cozmo, Miko, Kuri) are either expensive, closed-source, discontinued, or cloud-locked. PookieBot adopts an **Intel OpenBot** mechanical chassis approach and elevates it into a living social robot:
1. **Smartphone as Head, Face & High-Level Compute**: Uses an Android smartphone for procedural Pixar-style animated eyes, hardware-echo-cancelled microphones, front/rear cameras, speakers, and local web app display.
2. **Arduino as Real-Time Safety & Actuation Body**: Deterministic hardware-level fail-safe (<20cm ultrasonic emergency auto-stop) so the robot physically cannot crash into furniture or the baby's crib.
3. **Multimodal Physical AI Brain (Gemini 2.5/2.0 Flash)**: Cloud/local visual scene understanding with embodied tool calling (`drive()`, `turn()`, `approach()`, `navigate_to_target()`, `sing_lullaby()`, `follow_drawn_path()`).
4. **100% Sim-to-Real Digital Twin (MuJoCo 4.0)**: Rigorously calibrated 3D physics model in MuJoCo matching real TT motors, chassis mass, ballast CoM, sensor rays, and OpenCV vision pipelines.

---

## 2. Hardware Profile & Bill of Materials

- **Development Host**: HP ZBook G6, Windows 11, 32GB RAM.
- **Compute (High-Level)**: Android smartphone running Chrome (fullscreen `web/face.html` via WebSockets) + Laptop/Edge Brain.
- **Microcontroller (Low-Level)**: Arduino Nano (ATmega328P).
- **Chassis**: Standard 4WD transparent acrylic mobile robot car kit (Intel OpenBot mechanical geometry).
- **Motors**: 4x Yellow TT DC gear motors (1:48 gear ratio, 3–6V, ~0.4 Nm stall torque).
- **Motor Driver**: L298N or TB6612FNG dual H-bridge motor driver.
- **Obstacle Sensor**: HC-SR04 ultrasonic rangefinder mounted on front chassis bumper.
- **Power**: 2x 5V USB power banks (isolated power lines: Power Bank A for phone/logic, Power Bank B for motor driver to prevent inductive brownouts).
- **Interface**: USB-OTG adapter cable connecting smartphone to Arduino Nano via serial (115200 baud).

---

## 3. Software Environment & Dependencies

- **Virtual Environment**: Isolated at `d:\VKS\SelfMade\PookieBot\.venv` (Python 3.13.3).
- **Dependencies (`requirements.txt`)**:
  - `mujoco==4.0.1` (Physics simulation engine)
  - `numpy==2.5.5` (Vectorized math & array operations)
  - `websockets==17.4` (Asynchronous bidirectional face/brain communication)
  - `pyserial==3.5` (OpenBot Arduino serial communication)
  - `opencv-python==5.1.0` (Computer vision, color segmentation, ArUco fiducials)
  - `google-genai==3.6.1` (Gemini Multimodal VLM SDK)
  - `glfw==2.11.0`, `pyopengl==3.1.10` (MuJoCo interactive GUI viewer)
  - `mujoco-studio==4.0.1`, `mujoco-studio-wasm==4.0.1` (Studio sidecar tooling)

---

## 4. Codebase Architecture & File Map

```
d:\VKS\SelfMade\PookieBot\
├── .gitignore                    # Excludes .venv/, caches, dumps; preserves calibrated models
├── README.md                     # Public repo documentation
├── PROJECT_CONTEXT.md            # This dossier: single source of truth for Antigravity Projects
├── requirements.txt              # Production pip dependencies
├── run_pookiebot.py              # Master executable application (--gui, --interactive, --test, --mode sim|real)
│
├── core/                         # Core Python modules (1:1 Sim-to-Real parity)
│   ├── __init__.py               # Package exports
│   ├── hal.py                    # Hardware Abstraction Layer (SimRobotBridge & RealRobotBridge)
│   ├── face_bridge.py            # WebSocket bridge for animated face, audio, and mini-map
│   ├── vision.py                 # Vision pipeline (MuJoCo offscreen renderer & OpenCV capture)
│   ├── agent_brain.py            # Embodied Cognitive Mind (tool-calling & natural language dispatcher)
│   ├── visual_servoing.py        # Image-Based Visual Servoing (IBVS) & Color/ArUco Target Tracking
│   ├── path_follower.py          # Pure Pursuit path tracker for user-drawn 2D trajectories
│   └── vlm_agent.py              # Multimodal Gemini VLM reasoning with local perception fallback
│
├── simulation/                   # MuJoCo 4.0 Digital Twin
│   ├── models/
│   │   ├── pookiebot.xml         # Calibrated MJCF physics model (nursery, crib, targets, robot)
│   │   └── assets/               # Generated ArUco marker textures (aruco_0..3.png)
│   ├── pookie_sim.py             # Standalone GLFW physics viewer & keyboard teleop
│   └── record_demo.py            # Offscreen 1280x720 MP4 showcase video generator
│
├── web/                          # Expressive Animated Face & Web Controller
│   └── face.html                 # Disney-style procedural animated eye canvas + 2D Nursery Mini-Map
│
└── docs/                         # In-depth architectural & learning guides
    ├── LEARNING_LOG_AND_GUIDE.md # Live learning master log with 8 interactive labs
    ├── SYSTEM_ARCHITECTURE.md    # 3-tier architecture, serial protocols, fail-safes
    ├── HARDWARE_BOM.md           # Pinouts, schematic, wiring, power distribution
    └── OPENBOT_INTEGRATION.md    # OpenBot comparison, serial frame formats
```

---

## 5. Key Engineering Discoveries & Physics Calibrations

1. **MuJoCo Rangefinder Ray Orientation**:
   - MuJoCo `<rangefinder>` rays project strictly along the **site's local Z-axis**.
   - With `euler="0 0 0"`, the ray points directly at the ceiling.
   - Calibration: set `euler="0 90 0"` on `sonar_site` to pitch the ray 90° about Y, aligning it with the robot's forward +X axis.
2. **Rollover Prevention & Torque Limits**:
   - Uncapped `<velocity>` actuators apply infinite torque in a 5ms step (~98.7 Nm on a 500g chassis), causing backflips.
   - Calibration: bounded actuators to `forcerange="-0.4 0.4"` (matching physical TT motors), added a low-mounted 0.6kg battery ballast to lower Center of Mass below axle height ($z < 0.033\text{m}$), and added software acceleration ramping (`ramp_rate=0.8`).
3. **Camera Orientation via `xyaxes`**:
   - Euler angles can introduce roll ambiguity.
   - Calibration: used explicit direction vectors `xyaxes="0 -1 0  0.20 0 0.98"` for `robot_eye_camera` (12° downward pitch) and `xyaxes="0 -1 0  0.35 0 0.93"` for `third_person_view`.
4. **OpenGL Texture UV Inversion for ArUco**:
   - MuJoCo 2D box textures invert vertical UVs relative to OpenCV images.
   - Calibration: textures saved with `cv2.flip(img, 0)` so OpenCV's `ArucoDetector` detects simulated markers directly from the simulated camera feed.
5. **Simulation Stepping Loop Pacing**:
   - Sim stepping must be count-based (`steps = int(duration / dt)`) rather than wall-clock `time.time()` based, avoiding 100x speedups.

---

## 6. Current Operational State & Verification

All test suites and video recorders pass with 100% success:
- `.\.venv\Scripts\python.exe run_pookiebot.py --test`:
  - 1: FaceBridge Server
  - 2: HAL & Vision Initialization
  - 3: Camera Capture & Heuristics
  - 4: Natural Language Dispatcher & Emotions
  - 5: Nursery Lullaby Soothing Routine
  - 6: Sonar Obstacle Approach (halts cleanly at 22.0 cm)
  - 7: Celebratory Dance Routine
  - 8: Closed-Loop Visual Servoing to named target (`red_cube`)
  - 9: Pure Pursuit Trajectory Following along 4 waypoints
- `.\.venv\Scripts\python.exe -m core.visual_servoing`: Standalone target perception & servoing passed.
- `.\.venv\Scripts\python.exe -m core.path_follower`: Standalone pure pursuit passed.
- `.\.venv\Scripts\python.exe -m core.vlm_agent`: Standalone Gemini VLM & local perception passed.
- `pookiebot_showcase.mp4`: 171 high-res frames ($1280 \times 720$) recorded.

---

## 7. Immediate Next Steps / Roadmap

1. **Hardware Transition**:
   - Procure/gather chassis components (Arduino Nano, L298N, 4x TT motors, HC-SR04, USB-OTG cable).
   - Flash `openbot.ino` firmware to Arduino Nano via Arduino IDE.
   - Run bench test: `.\.venv\Scripts\python.exe run_pookiebot.py --mode real --port COM3 --interactive`.
2. **Physical Phone Docking**:
   - Mount Android phone onto chassis cradle.
   - Open `web/face.html` in Chrome on the phone, tap **⛶ Fullscreen**.
3. **Advanced Nursery Physical AI**:
   - Voice trigger activation / wake-word ("Hey Pookie").
   - Lullaby nightlight mode (dimmed warm screen eyes playing gentle Brahms lullaby).
   - Audio cry detection reflex (alerting parents and driving toward the crib).
