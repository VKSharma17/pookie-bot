"""
PookieBot Face Bridge Server
============================
Lightweight, asynchronous WebSocket server bridging the cognitive brain
to the expressive animated HTML5 face running on the phone or browser.

Supported Downlink Events:
    {"type": "emotion", "emotion": "HAPPY" | "CURIOUS" | "SLEEPY" | "LOVING" | "NEUTRAL"}
    {"type": "sound", "sound": "happy" | "curious" | "love" | "sleepy" | "chirp"}
    {"type": "gaze", "x": -25.0, "y": 10.0}
    {"type": "blink"}
    {"type": "response", "text": "I moved forward!"}

Supported Uplink Events (from Browser / Phone):
    {"type": "voice_command", "text": "dance"}
    {"type": "robot_command", "cmd": "approach"}
    {"type": "tap", "region": "screen"}
"""

import asyncio
import json
import threading
import websockets
from typing import Set, Optional, Callable, Any


class FaceBridgeServer:
    """Manages real-time bidirectional communication with web/face.html."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.server_thread: Optional[threading.Thread] = None
        self.on_touch_callback: Optional[Callable[[str], None]] = None
        self.on_command_callback: Optional[Callable[[str], Any]] = None
        self.on_path_callback: Optional[Callable[[list], Any]] = None
        self._running = False

    async def _handler(self, websocket):
        """Handle incoming client connections."""
        self.clients.add(websocket)
        try:
            # Send initial state
            await websocket.send(json.dumps({"type": "emotion", "emotion": "HAPPY"}))
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type in ("voice_command", "robot_command") and self.on_command_callback:
                        cmd_text = data.get("text") or data.get("cmd") or ""
                        if cmd_text:
                            # Run command callback in separate worker thread to avoid blocking async loop
                            def run_cmd(text):
                                reply = self.on_command_callback(text)
                                if reply:
                                    self.send_response(str(reply))

                            threading.Thread(target=run_cmd, args=(cmd_text,), daemon=True).start()

                    elif msg_type == "follow_path" and self.on_path_callback:
                        waypoints = data.get("waypoints", [])
                        if waypoints:
                            def run_path(pts):
                                reply = self.on_path_callback(pts)
                                if reply:
                                    self.send_response(str(reply))

                            threading.Thread(target=run_path, args=(waypoints,), daemon=True).start()

                    elif msg_type == "tap" and self.on_touch_callback:
                        self.on_touch_callback(data.get("region", "screen"))

                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        finally:
            self.clients.discard(websocket)

    def _broadcast(self, payload: dict):
        """Thread-safe broadcast helper."""
        if not self.loop or not self.clients:
            return
        message = json.dumps(payload)
        for ws in list(self.clients):
            try:
                asyncio.run_coroutine_threadsafe(ws.send(message), self.loop)
            except Exception:
                pass

    def set_emotion(self, emotion: str):
        """Change facial expression state."""
        self._broadcast({"type": "emotion", "emotion": emotion.upper()})

    def play_sound(self, sound_type: str):
        """Trigger procedural chirp or chime."""
        self._broadcast({"type": "sound", "sound": sound_type.lower()})

    def look_at(self, gaze_x: float, gaze_y: float):
        """Direct eye gaze coordinates (pixels offset)."""
        self._broadcast({"type": "gaze", "x": float(gaze_x), "y": float(gaze_y)})

    def blink(self):
        """Trigger immediate eyelid blink."""
        self._broadcast({"type": "blink"})

    def send_response(self, text: str):
        """Send verbal text response to face display / speech synthesizer."""
        self._broadcast({"type": "response", "text": text})

    def broadcast_telemetry(self, telemetry: dict):
        """Broadcast live robot state (pose, sonar, safety) to web client."""
        self._broadcast({"type": "telemetry", "telemetry": telemetry})

    def start(self):
        """Start the WebSocket server in a background daemon thread."""
        if self._running:
            return
        self._running = True

        def run_server():
            async def main():
                self.loop = asyncio.get_running_loop()
                try:
                    async with websockets.serve(self._handler, self.host, self.port):
                        print(f"[FaceBridgeServer] WebSocket server listening on ws://{self.host}:{self.port}")
                        while self._running:
                            await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"[FaceBridgeServer] Error running server: {e}")

            try:
                asyncio.run(main())
            except Exception:
                pass

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def stop(self):
        """Stop server."""
        self._running = False
