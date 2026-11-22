# PookieBot: System Architecture & Design Specification

> **A Living Physical AI Social Robot for the Nursery & Home**  
> *Dedicated with love to our one-month-old baby girl.*

---

## 1. Executive Summary & Vision

**PookieBot** bridges the low-cost, open-source mechanical excellence of **Intel OpenBot** with modern **Embodied Multimodal Physical AI (LLMs & VLMs)** and **Pixar-inspired Human-Robot Interaction (HRI)**.

Traditional DIY robotics projects often fail in home environments due to three bottlenecks:
1. **The Sensor/Actuator Wiring Nightmare**: Connecting discrete cameras, microphones, loud speakers, displays, and compute modules to a single board causes severe thermal, electrical noise, and acoustic feedback issues.
2. **Lack of Emotional Resonance**: Robots like standard OpenBot or ROS turtlebots act purely as robotic utility vehicles with no expressive face, no vocal warmth, and no personality.
3. **High Latency Cognitive Disconnect**: Attempting to run large multi-billion parameter multimodal models directly on a microcontroller or low-power board causes 5-10 second reaction delays, destroying conversational presence.

**The PookieBot Solution: The "Golden Triad" Architecture**
* **The Body (OpenBot-Compatible Microcontroller)**: Deterministic, real-time motor control, wheel odometry, and hardware-level ultrasonic collision override (<50ms fail-safe).
* **The Head & Senses (Android/iOS Smartphone)**: A single integrated unit providing a vibrant OLED/LCD animated face, camera, hardware echo-cancelled dual-microphones, stereo speakers, and battery.
* **The Mind (Cloud API / Local Laptop AI Server)**: Sub-second multimodal reasoning via Gemini 2.0 Flash / OpenAI Realtime / Groq Llama-3.3, driving the robot through structured physical tool calling (`drive`, `turn`, `express`, `look_at`, `sing_lullaby`).
* **The Digital Twin (MuJoCo 4.0 Physics Simulation)**: 100% digital validation of physics, obstacle avoidance, and agent control on your HP ZBook prior to physical assembly.

---

## 2. High-Level System Architecture

```mermaid
graph TD
    subgraph S_HEAD["Perception & Expressive Head (Smartphone)"]
        MIC["Stereo Mic Array (HW Noise/Echo Cancellation)"] --> STT["Fast Streaming Audio (WebRTC / WebSocket)"]
        CAM["HD Camera (Forward / Environment)"] --> VLM["Visual Perception Stream"]
        TTS["Expressive Audio & Chirp Engine"] --> SPK["Loudspeaker"]
        ANIM["Procedural Eye Engine (HTML5 Canvas / WebGL)"] --> SCR["Smartphone Screen Face"]
    end

    subgraph S_MIND["Cognitive Mind (Local Laptop Server or Cloud)"]
        STT --> AGENT["Physical AI Agent Core (LLM + VLM)"]
        VLM --> AGENT
        AGENT -->|"Tool Calls: drive(), turn(), express(), sing()"| DISPATCH["Action Dispatcher"]
        DISPATCH --> TTS
        DISPATCH --> ANIM
    end

    subgraph S_BODY["Physical Body & Actuation (Arduino / ESP32)"]
        DISPATCH -->|"USB-OTG Serial / Bluetooth (115200 baud)"| BRIDGE["OpenBot Serial Protocol Bridge"]
        BRIDGE -->|"PWM Control: c<left>,<right>"| DRV["Motor Driver (L298N / TB6612)"]
        DRV --> MOT["4x DC Gear TT-Motors + Wheels"]
        SONIC["HC-SR04 Ultrasonic Rangefinder"] -->|"Safety Override Stop (s<dist>)"| BRIDGE
        BAT["Battery Voltage Divider (v<volts>)"| BRIDGE
    end

    subgraph S_SIM["Digital Twin Simulation (MuJoCo 4.0)"]
        DISPATCH -.->|"Virtual Serial Bridge (Mock Protocol)"| SIM_CAR["MuJoCo PookieBot Simulation"]
        SIM_CAR -.->|"Simulated Rangefinder & Encoders"| DISPATCH
    end
```

---

## 3. Communication Protocol (OpenBot-Compatible Protocol)

PookieBot maintains strict binary/ASCII compatibility with the battle-tested **OpenBot protocol** over USB-OTG serial (115,200 baud) or WebSocket/Bluetooth:

### A. Downlink: High-Level Brain $\rightarrow$ Microcontroller
| Command | Format | Example | Action |
| :--- | :--- | :--- | :--- |
| **Drive Motors** | `c<left>,<right>\n` | `c128,128\n` | Drive forward at 50% PWM (-255 to 255 range). |
| **Rotate** | `c<left>,<right>\n` | `c-120,120\n` | Pivot turn left on spot. |
| **Emergency Stop** | `c0,0\n` | `c0,0\n` | Instant dynamic braking. |
| **LED Indicator** | `i<left>,<right>\n` | `i1,0\n` | Left turn signal / status LED on. |

### B. Uplink: Microcontroller $\rightarrow$ Smartphone Brain (Telemetry)
| Prefix | Payload Format | Example | Semantic Meaning |
| :--- | :--- | :--- | :--- |
| **`s`** | `s<distance_cm>\n` | `s18\n` | Front ultrasonic obstacle distance is 18 cm. |
| **`w`** | `w<left_rpm>,<right_rpm>\n` | `w120,118\n` | Optical encoder rotational velocity. |
| **`v`** | `v<volts>\n` | `v7.4\n` | Battery voltage level (low-battery alert). |

---

## 4. Emotional HRI: The Living Face Engine

Unlike industrial robots, PookieBot is designed for a newborn nursery. Emotional safety and warmth dictate the facial interface:
1. **Procedural Eye Dynamics**:
   - Eyes are dynamically drawn rounded rectangles with soft gradients.
   - Natural, stochastic blinking every 3 to 6 seconds.
   - Saccadic eye movements (occasional quick micro-shifts mimicking natural curiosity).
2. **Emotional State Machine**:
   - `HAPPY`: Upward arched eyelids, wide pupils, subtle bounce animation.
   - `CURIOUS`: Tilted eye axis, widened pupils, tracking movement.
   - `SLEEPY`: Half-closed drooping lids, slow blinking, soft breathing pulse.
   - `LOVING`: Soft heart/star pupil highlight, warm pastel hue.
   - `ALERT`: Wide eyes, fast saccades when obstacle is detected.
3. **Sound Effects**:
   - Non-verbal emotive chirps, purrs, and soft melodic chimes accompany state transitions, inspired by Anki Vector and Pixar's Wall-E.

---

## 5. Sim-to-Real Architecture (MuJoCo Digital Twin)

Before soldering wires or mounting hardware, the entire robot is simulated in **MuJoCo 4.0**:
- **Chassis Dynamics**: 4-wheel differential-drive physics with friction, slip, and accurate mass distribution.
- **Sensor Models**: Forward-facing optical rangefinder simulating the HC-SR04 ultrasonic sensor.
- **Virtual Serial Bridge**: The Python simulation script accepts the exact same `c<left>,<right>\n` strings used by the physical robot, ensuring complete behavioral parity between code run on the laptop and code executed on the real chassis.
