# 🧸 PookieBot: A Living Physical AI Social Robot

> **Dedicated with love to our one-month-old baby girl.**  
> *An interactive, mobile home companion that brings together low-cost robotics, emotive face design, and modern Physical AI (LLMs & VLMs).*

---

## 🌟 Vision & Project Goals

PookieBot is a DIY living social robot designed for the nursery and home. Inspired by commercial companion robots (Anki Vector, Cozmo, Mayfield Kuri) and powered by open robotics platforms (**Intel OpenBot**), PookieBot bridges the physical and digital world through:

1. **An Expressive Living Soul**: High-resolution procedural animated eyes displayed on an Android smartphone screen with natural blinking, pupil dilation, emotional states (`HAPPY`, `CURIOUS`, `SLEEPY`, `LOVING`), and cute R2-D2/Wall-E-style chirps.
2. **Deterministic Nursery Safety**: Hardware-level fail-safe obstacle avoidance (<20cm auto-stop) implemented on an Arduino microcontroller so the robot never bumps into cribs, furniture, or toys.
3. **Multimodal Physical AI Brain**: Real-time voice interaction and visual awareness powered by modern fast models (Gemini 2.0 Flash / OpenAI Realtime / Groq) with structured physical tool calling (`drive()`, `turn()`, `express()`, `sing_lullaby()`).
4. **Simulation-First Engineering (MuJoCo 4.0)**: A 100% digital twin built and verified in MuJoCo physics on Windows, enabling testing of control loops, obstacle sensing, and teleoperation before assembling physical hardware.

---

## 🏗️ Architecture: The 3-Tier "Golden Triad"

```
+-------------------------------------------------------------+
|               TIER 3: COGNITIVE MIND (AI BRAIN)             |
|  • Multimodal Agent (Gemini 2.0 Flash / OpenAI Realtime)    |
|  • Voice STT & Expressive Audio Engine                      |
|  • Nursery Guardrails & Personality State Machine           |
|  • Tool Calling: drive(), turn(), express(), sing_lullaby() |
+------------------------------+------------------------------+
                               | High-Level Action Commands
+------------------------------V------------------------------+
|             TIER 2: PERCEPTION & FACE (SMARTPHONE)          |
|  • Procedural Eye Engine (web/face.html)                    |
|  • Hardware Echo-Cancelled Dual Microphones & Loudspeakers  |
|  • Forward/Environment HD Camera (Visual Grounding)         |
|  • OpenBot USB-Serial Driver (Translates tools to c<l>,<r>) |
+------------------------------+------------------------------+
                               | Low-Level Serial: "c120,120\n"
+------------------------------V------------------------------+
|            TIER 1: PHYSICAL BODY (ARDUINO / CHASSIS)        |
|  • openbot.ino Firmware (115200 Baud)                       |
|  • Motor PWM H-Bridge Driver (L298N / TB6612)               |
|  • Ultrasonic Hardware Emergency Stop (<20cm fail-safe)     |
|  • 4x Yellow TT DC Motors + Rubber Wheels                   |
+-------------------------------------------------------------+
```

---

## 🚀 Quickstart: Try It Now!

All commands run inside the isolated virtual environment `.venv`:

### 1. Run the Full Automated Integration Test
```powershell
.\.venv\Scripts\python.exe run_pookiebot.py --test
```
*Verifies HAL, WebSocket Face Server, MuJoCo Offscreen Vision, Brain Tools, and 20cm Obstacle Safety Cutoff in 3 seconds!*

### 2. Interactive 3D Simulation with Live Animated Face
Launch both the 3D physics world and the browser face connected live over WebSockets:

```powershell
.\.venv\Scripts\python.exe run_pookiebot.py --gui --interactive
```
*Try typing: `happy`, `love`, `sleep`, `look`, `forward`, `patrol`, or `stop`!*

### 3. Standalone Teleoperation Viewer
```powershell
.\.venv\Scripts\python.exe simulation/pookie_sim.py
```

---

## 📚 Documentation & Learning Guides

* 🌟 **[PROJECT_CONTEXT.md](file:///d:/VKS/SelfMade/PookieBot/PROJECT_CONTEXT.md)**: **Single Source of Truth for Antigravity Projects**—complete state, calibrations, architecture, and handover notes.
* 🌟 **[LEARNING_LOG_AND_GUIDE.md](file:///d:/VKS/SelfMade/PookieBot/docs/LEARNING_LOG_AND_GUIDE.md)**: **The Live Learning Master Document**—detailed explanation of what, why, and how every module was built, SOTA as of Nov 2026, 8 interactive hands-on labs (including IBVS visual servoing, Pure Pursuit path following, and Gemini VLM reasoning), and Sim-to-Real hardware transfer guide.
* 📖 **[SYSTEM_ARCHITECTURE.md](file:///d:/VKS/SelfMade/PookieBot/docs/SYSTEM_ARCHITECTURE.md)**: Deep architectural dive into the 3-tier computing breakdown, communication protocols, and safety models.
* 🛠️ **[HARDWARE_BOM.md](file:///d:/VKS/SelfMade/PookieBot/docs/HARDWARE_BOM.md)**: Exact component list, wiring pinouts, power distribution, and 3D printing options.
* 🤖 **[OPENBOT_INTEGRATION.md](file:///d:/VKS/SelfMade/PookieBot/docs/OPENBOT_INTEGRATION.md)**: How PookieBot takes Intel OpenBot's mechanical chassis and USB-OTG serial link to the next level.
* 🗺️ **[System Architecture & 30-Day Plan Artifact](file:///C:/Users/admin/.gemini/antigravity-ide/brain/87e44f1f-aeb9-417d-962b-adb259a6b81a/system_architecture_and_roadmap.md)**: The original foundational design analysis.

---

## 📅 Next Phased Steps

1. **Phase 1: Simulation Tuning & Multimodal Voice Agent (Active)**
   * Connect Python AI agent with tool-calling directly to the `VirtualOpenBotBridge`.
   * Add Whisper / Groq / OpenAI Realtime audio loop on the laptop.
2. **Phase 2: Arduino Firmware & Hardware Bring-Up**
   * Flash `openbot.ino` to Arduino Nano.
   * Bench-test motor driver and HC-SR04 ultrasonic sensor.
3. **Phase 3: Embodiment & Nursery Polishing**
   * Dock phone onto chassis via USB-OTG.
   * Add nursery routines (soft night-light eyes, lullaby timer, whisper mode).
