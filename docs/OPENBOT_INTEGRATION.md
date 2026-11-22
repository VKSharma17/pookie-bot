# OpenBot Integration Strategy for PookieBot

This document details how PookieBot takes the mechanical and firmware foundations of **Intel OpenBot** (`ob-f/OpenBot`) and elevates it into a living social robot.

---

## 1. What OpenBot Provides (The Foundation)

Intel's OpenBot project solved the mechanical and electrical barrier of entry for smartphone robotics:
1. **$50 Mechanical BOM**: Standard 3D-printable chassis housing 4 yellow DC TT-motors, L298N/TB6612 motor driver, and battery pack.
2. **Standard Microcontroller Firmware (`openbot.ino`)**:
   - Real-time PWM generation on hardware timer pins.
   - Interrupt-driven optical wheel odometry.
   - Front ultrasonic distance measurement (HC-SR04).
3. **Hardware USB-OTG Serial Link**:
   - Android smartphones running USB-Host mode can open a physical serial port to the Arduino at 115,200 baud without Bluetooth pairing delays or Wi-Fi dropouts.

---

## 2. Where OpenBot Stops & PookieBot Begins

| Capability | Standard OpenBot | PookieBot Evolution |
| :--- | :--- | :--- |
| **Primary Use Case** | Self-driving car experiments (lane following, person tracking via MobileNet TFLite). | Social, interactive physical AI companion for child/family. |
| **Human Interface** | Pure utility UI (telemetry graphs, control sliders, debug text). | **Living Emotional Face**: Animated procedural eyes with Disney squash & stretch, emotion states, and gaze tracking. |
| **Acoustic Interaction** | None (silent or beep tones). | **Bilingual Voice Loop**: Natural voice STT $\rightarrow$ Multimodal LLM $\rightarrow$ Low-latency emotive TTS with lullaby routines. |
| **Cognitive Autonomy** | Hardcoded heuristics and pre-trained classification models. | **Embodied Physical AI**: Multimodal VLM reasoning with tool calling (`drive`, `turn`, `express`, `inspect_scene`, `sing_lullaby`). |
| **Digital Twin** | Minimal or Unity-only simulation. | **MuJoCo 4.0 Digital Twin**: Physically accurate differential drive simulation with obstacle avoidance and 1:1 serial protocol parity. |

---

## 3. The 3-Tier Layered Architecture

```
+-------------------------------------------------------------+
|               TIER 3: COGNITIVE MIND (AI BRAIN)             |
|  • Multimodal Agent (Gemini 2.0 Flash / OpenAI Realtime)    |
|  • Voice STT & Expressive TTS / Sound FX                    |
|  • Nursery Guardrails & Personality State Machine           |
|  • Tool Calling: drive(), turn(), express(), sing_lullaby() |
+------------------------------+------------------------------+
                               | High-Level Action Commands
+------------------------------V------------------------------+
|             TIER 2: PERCEPTION & FACE (SMARTPHONE)          |
|  • Procedural Eye Engine (HTML5 Canvas / Flutter)           |
|  • Hardware Echo-Cancelled Microphone & Stereo Loudspeaker  |
|  • Forward/Environment HD Camera (Visual Grounding)         |
|  • OpenBot USB-Serial Driver (Translates tools to c<l>,<r>) |
+------------------------------+------------------------------+
                               | Low-Level Serial Commands: "c120,120\n"
+------------------------------V------------------------------+
|            TIER 1: PHYSICAL BODY (ARDUINO / CHASSIS)        |
|  • openbot.ino Firmware (115200 Baud)                       |
|  • Motor PWM H-Bridge Driver (L298N / TB6612)               |
|  • Ultrasonic Hardware Emergency Stop (<20cm fail-safe)     |
|  • 4x Yellow TT DC Motors + Rubber Wheels                   |
+-------------------------------------------------------------+
```

---

## 4. Hardware Connection Steps

1. **Flash Firmware to Arduino**:
   - Use Arduino IDE or CLI to flash `openbot.ino` to your Arduino Nano or Uno.
2. **Mount Phone**:
   - Slide your Android phone into the 35° angled cradle on the chassis.
3. **Plug USB-OTG**:
   - Plug the USB-OTG adapter into the phone's charging port and connect the USB cable to the Arduino Nano.
4. **Launch Web Face or Client App**:
   - Open the full-screen browser face (`face.html`) or OpenBot bridge app. The phone establishes serial connection automatically.
