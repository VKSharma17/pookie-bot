# PookieBot: Bill of Materials (BOM) & Hardware Integration Guide

This guide details the exact components, wiring connections, and power distribution needed to physically build PookieBot using standard, low-cost OpenBot-compatible components.

---

## 1. Complete Bill of Materials

| Category | Component Description | Recommended Model | Est. Cost (USD/INR) | Purpose / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Microcontroller** | Arduino Nano (or Uno / ESP32) | ATmega328P Nano with Type-C / Mini-USB | ~$4 / ₹350 | Runs OpenBot firmware (`openbot.ino`). Real-time motor PWM & ultrasonic safety. |
| **Motors** | 4x Yellow TT DC Gear Motors | 1:48 gear ratio, 3V–6V DC with rubber wheels | ~$8 / ₹600 (4-pack) | Standard robot car kit motors. Quiet, reliable torque at low RPM. |
| **Motor Driver** | Dual H-Bridge Motor Driver | L298N (Red Board) or TB6612FNG (More efficient) | ~$3 / ₹250 | Drives left and right motor banks. TB6612 is smaller and generates less heat. |
| **Ultrasonic Sensor** | Proximity / Rangefinder | HC-SR04 (or HC-SR04P 3.3V/5V compatible) | ~$1.50 / ₹120 | Mounted on front bumper for fail-safe collision avoidance (<20cm). |
| **Wheel Encoders (Optional)** | 2x Optical Speed Sensors | 20-slot encoder discs + slotted optical sensor | ~$2 / ₹180 | Measures wheel rotations and distance traveled (odometry). |
| **Body / Chassis** | OpenBot 3D Printed Body or Acrylic Kit | OpenBot DIY 3D Chassis (STL) or 4WD Acrylic Plate | ~$10 / ₹800 | Holds phone at 30°–45° angle, encloses motors and wiring neatly. |
| **Head (Display & Senses)**| Android Smartphone | Any functional Android phone (Android 8.0+) | Already owned | Acts as the face screen, HD camera, stereo mic, speaker, and Wi-Fi hub. |
| **Data Cable** | USB-OTG Cable / Adapter | Type-C (or Micro-USB) to USB-A Female + Nano cable | ~$2 / ₹150 | Connects phone directly to Arduino Nano via hardware serial. |
| **Power Supply (Motors)**| Battery Pack | 2x 18650 Li-ion cells (7.4V) + Holder with switch | ~$6 / ₹450 | Supplies clean 7.4V to motor driver (L298N) and VIN of Arduino. |
| **Power Supply (Phone)** | Power Bank (Optional backup) | Ultra-slim 5000mAh power bank | Already owned | Keeps phone charged during long nursery play sessions. |

---

## 2. Electrical Wiring Schematic

```
                          +------------------------+
                          |   2x 18650 Li-Ion      |
                          |   Battery Pack (7.4V)  |
                          +-----------+------------+
                                      |
                      +---------------+---------------+
                      | (+)                           | (-) GND
                      V                               V
             +-----------------+             +-----------------+
             | L298N 12V In    |             | Common Ground   |
             +-----------------+             +--------+--------+
                      |                               |
                      | 5V Out (Regulated)            |
                      +---------------+               |
                                      |               |
                                      V               V
                              +---------------+---------------+
                              | Arduino Nano  | Arduino GND   |
                              | VIN / 5V Pin  | Pin           |
                              +---------------+---------------+

   [Arduino Nano Pins]                          [L298N Motor Driver]
   -------------------                          --------------------
   D5 (PWM) ----------------------------------> ENA (Left Motor Speed)
   D6 ----------------------------------------> IN1 (Left Motor Fwd)
   D7 ----------------------------------------> IN2 (Left Motor Rev)
   D8 ----------------------------------------> IN3 (Right Motor Rev)
   D9 ----------------------------------------> IN4 (Right Motor Fwd)
   D10 (PWM) ---------------------------------> ENB (Right Motor Speed)

   [Arduino Nano Pins]                          [HC-SR04 Ultrasonic]
   -------------------                          --------------------
   5V ----------------------------------------> VCC
   GND ---------------------------------------> GND
   D11 ---------------------------------------> Trigger Pin
   D12 ---------------------------------------> Echo Pin

   [Arduino USB Port]                           [Smartphone Head]
   ------------------                           -----------------
   Mini-USB / Type-C <====== USB-OTG Cable ======> Phone Charging Port
```

---

## 3. Chassis & 3D Fabrication Options

### Option A: The OpenBot Official 3D-Printable Body (Recommended)
* **Source**: [OpenBot GitHub Body Repository](https://github.com/ob-f/OpenBot/tree/master/body)
* **Print Time**: ~8 hours on standard Ender-3 / Bambu / Prusa.
* **Key Feature**: Has an integrated angled cradle designed specifically to hold standard smartphones securely, with cutouts for the rear camera and USB port.

### Option B: The "No 3D-Printer" Acrylic / Cardboard Rapid Prototype
* If you don't have immediate access to a 3D printer:
  1. Use the standard transparent dual-deck acrylic 4WD car chassis (available in all Arduino starter car kits).
  2. Use an inexpensive adjustable desktop phone stand or custom foam block velcroed to the top acrylic plate at a 35° angle.
  3. This gets you up and running within 2 hours!

---

## 4. Safety Considerations for Newborn Nursery
1. **Low Speed Tuning**: TT motors can drive up to 0.5 m/s. For nursery safety, maximum PWM is capped in firmware to 100/255 (~0.15 m/s or gentle walking speed).
2. **Smooth Acceleration (Ramping)**: Jerky start/stop motions can frighten a baby. The Arduino firmware applies a gentle low-pass filter to motor commands so starts and stops glide smoothly.
3. **Hardwired Obstacle Stop**: If the ultrasonic sensor detects any object within 20cm, the Arduino hardware automatically overrides all motor commands and halts immediately.
4. **Soft Bumper Cladding**: Adding foam weather-stripping or silicone edge protectors around the front bumper prevents any damage to crib legs or furniture.
