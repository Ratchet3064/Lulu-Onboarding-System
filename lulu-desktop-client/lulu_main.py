import sys
import time
import math
import ctypes
import json
import requests

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QPoint, QUrl
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QRadialGradient, 
    QLinearGradient, QPen, QPolygonF, QGuiApplication
)
from lulu_voice import LuluVoiceEngine
from ui_scanner import LuluUIScanner

LULU_THEME_HEX = "#fc038c"
LULU_HOT_CORE_HEX = "#ff99d6"
API_BASE_URL = "http://127.0.0.1:5000"
WS_BASE_URL = "ws://127.0.0.1:5000/ws/client"

class LuluOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lulu Overlay HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.showFullScreen()

        self.voice = LuluVoiceEngine()
        self.scanner = LuluUIScanner()

        self.cur_x = 300.0
        self.cur_y = 300.0
        self.target_x = 300.0
        self.target_y = 300.0
        self.instruction = "Connecting to Lulu Backend Server..."
        self.active_wf_title = "Onboarding Hub"

        self.phase = 0.0
        self.ripple_radius = 10.0
        self.ripple_alpha = 220

        # Multi-Workflow Cache
        self.known_workflows = []
        self.workflow = self.fetch_initial_workflow()
        self.steps = self.workflow.get("steps", [])
        self.current_step_idx = 0
        self.step_start_time = time.time()
        self.spoken_current_step = False
        self.telemetry_results = []
        self.workflow_finished = False

        # WebSocket Client Initialization
        self.ws = QWebSocket()
        self.ws.connected.connect(self.on_ws_connected)
        self.ws.disconnected.connect(self.on_ws_disconnected)
        self.ws.textMessageReceived.connect(self.on_ws_message_received)
        self.connect_websocket()

        # Reconnect Timer for WebSocket
        self.ws_reconnect_timer = QTimer(self)
        self.ws_reconnect_timer.timeout.connect(self.check_ws_reconnect)
        self.ws_reconnect_timer.start(3000)

        # Animation Loop (60 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate_lulu)
        self.anim_timer.start(16)

        # UI Element Scanner Loop (350 ms)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.update_fsm_and_scan)
        self.scan_timer.start(350)

        # Periodically refresh known workflows list (every 10 seconds)
        self.wf_refresh_timer = QTimer(self)
        self.wf_refresh_timer.timeout.connect(self.refresh_known_workflows)
        self.wf_refresh_timer.start(10000)
        self.refresh_known_workflows()

    # ==========================================
    # WEBSOCKET REAL-TIME SYNC
    # ==========================================
    def connect_websocket(self):
        try:
            print(f"[Lulu WebSocket] Connecting to {WS_BASE_URL}...")
            self.ws.open(QUrl(WS_BASE_URL))
        except Exception as e:
            print(f"[Lulu WebSocket Error]: {e}")

    def on_ws_connected(self):
        print("[Lulu WebSocket] 🟢 Connected to Backend Live Stream!")

    def on_ws_disconnected(self):
        print("[Lulu WebSocket] 🔴 Disconnected from Backend. Will retry...")

    def check_ws_reconnect(self):
        if self.ws.state() == QWebSocket.SocketState.UnconnectedState:
            self.connect_websocket()

    def on_ws_message_received(self, message):
        try:
            msg = json.loads(message)
            msg_type = msg.get("type")
            print(f"[Lulu WebSocket Event Received]: {msg_type}")

            if msg_type in ("WORKFLOW_UPDATED", "WORKFLOW_SWITCHED", "INITIAL_WORKFLOW"):
                new_wf = msg.get("workflow")
                if new_wf:
                    self.load_workflow(new_wf, is_live_update=(msg_type == "WORKFLOW_UPDATED"))
        except Exception as e:
            print(f"[Lulu WS Message Error]: {e}")

    # ==========================================
    # MULTI-WORKFLOW LOGIC
    # ==========================================
    def fetch_initial_workflow(self):
        try:
            res = requests.get(f"{API_BASE_URL}/api/workflow/active", timeout=5)
            wf = res.json()
            self.active_wf_title = wf.get("title", "Onboarding Hub")
            return wf
        except Exception as e:
            print(f"[API Warning] Fallback default workflow: {e}")
            return {
                "workflow_id": "wf_fallback",
                "title": "Customer Refund Onboarding Guide",
                "window_title": "Enterprise Billing Portal",
                "steps": []
            }

    def refresh_known_workflows(self):
        try:
            res = requests.get(f"{API_BASE_URL}/api/workflows", timeout=3)
            if res.status_code == 200:
                self.known_workflows = res.json()
        except Exception:
            pass

    def load_workflow(self, wf, is_live_update=False):
        """Loads or updates workflow dynamically without requiring application restart."""
        self.workflow = wf
        self.active_wf_title = wf.get("title", "Onboarding Guide")
        self.steps = wf.get("steps", [])

        if is_live_update:
            # Preserve current step progress if still within bounds
            if self.current_step_idx >= len(self.steps):
                self.current_step_idx = max(0, len(self.steps) - 1)
            self.spoken_current_step = False
            self.step_start_time = time.time()
            print(f"[Lulu HUD] Live workflow updated: {len(self.steps)} steps loaded.")
        else:
            # Complete switch to new workflow
            self.current_step_idx = 0
            self.step_start_time = time.time()
            self.spoken_current_step = False
            self.telemetry_results = []
            self.workflow_finished = False
            print(f"[Lulu HUD] Switched to workflow: '{self.active_wf_title}'")
            self.voice.speak(f"Loading {self.active_wf_title}.")

    def send_telemetry(self, step_obj, duration):
        """Pushes step completion telemetry via WebSocket, falling back to HTTP."""
        payload = {
            "workflow_id": self.workflow.get("workflow_id", "default"),
            "step_num": step_obj["step_num"],
            "target_button": step_obj["target_button"],
            "duration_seconds": duration
        }

        # Zero-latency push over WebSocket
        if self.ws.isValid():
            try:
                self.ws.sendTextMessage(json.dumps({
                    "type": "TELEMETRY_LOG",
                    "data": payload
                }))
                print(f"[Lulu Telemetry] Sent via WebSocket: Step {step_obj['step_num']} ({duration}s)")
                return
            except Exception as e:
                print(f"[WS Telemetry Error]: {e}")

        # Fallback HTTP REST upload
        try:
            requests.post(f"{API_BASE_URL}/api/telemetry", json=payload, timeout=2.0)
            print(f"[Lulu Telemetry] Sent via HTTP: Step {step_obj['step_num']} ({duration}s)")
        except Exception as e:
            print(f"[Telemetry Upload Warning]: {e}")

    def physical_to_logical(self, phys_x, phys_y):
        screen = QGuiApplication.screenAt(QPoint(int(phys_x), int(phys_y)))
        if not screen:
            screen = QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio()
        local_pos = self.mapFromGlobal(QPoint(int(phys_x / dpr), int(phys_y / dpr)))
        return float(local_pos.x()), float(local_pos.y())

    # ==========================================
    # SCANNER & FINITE STATE MACHINE (FSM)
    # ==========================================
    def update_fsm_and_scan(self):
        if self.workflow_finished or not self.steps:
            return

        current_window_title = self.workflow.get("window_title", "Enterprise Billing Portal")
        elements = self.scanner.scan_window(current_window_title)

        # Multi-App Auto-Detection:
        # If the target window is not open, check if another known workflow window is open!
        if not elements:
            for other_wf in self.known_workflows:
                other_window = other_wf.get("window_title")
                if other_window and other_window != current_window_title:
                    other_elements = self.scanner.scan_window(other_window)
                    if other_elements:
                        print(f"[Lulu Auto-Detect] Found open app '{other_window}' -> Auto-switching to '{other_wf.get('title')}'")
                        self.load_workflow(other_wf, is_live_update=False)
                        return

            self.instruction = f"Waiting for '{current_window_title}'..."
            return

        current_step = self.steps[self.current_step_idx]

        # 1. Check if current step was completed
        if self.scanner.is_text_on_screen(elements, current_step["verify_screen_text"]):
            duration = round(time.time() - self.step_start_time, 1)
            self.telemetry_results.append(f"Step {current_step['step_num']}: {duration}s")
            
            # Send live telemetry to Manager Dashboard with zero delay!
            self.send_telemetry(current_step, duration)

            self.current_step_idx += 1
            self.step_start_time = time.time()
            self.spoken_current_step = False

            if self.current_step_idx >= len(self.steps):
                self.workflow_finished = True
                summary = " | ".join(self.telemetry_results)
                self.instruction = f"🎉 Complete! Telemetry Sent: {summary}"
                self.voice.speak("Awesome job! Your onboarding telemetry has been sent to the Manager Dashboard.")
                return

            current_step = self.steps[self.current_step_idx]

        # 2. Locate target element center
        coords = self.scanner.find_element_center(elements, current_step["target_button"])
        if coords:
            lx, ly = self.physical_to_logical(coords[0], coords[1])
            self.target_x, self.target_y = lx, ly
            self.instruction = current_step["badge_text"]

            if not self.spoken_current_step:
                self.voice.speak(current_step["voice_text"])
                self.spoken_current_step = True

    # ==========================================
    # NEON VISUAL ANIMATION & RENDERING
    # ==========================================
    def animate_lulu(self):
        # Smooth lerp physics
        self.cur_x += (self.target_x - self.cur_x) * 0.22
        self.cur_y += (self.target_y - self.cur_y) * 0.22
        self.phase += 0.08

        # Sonar ripple physics
        self.ripple_radius += 0.85
        self.ripple_alpha = max(0, int(240 * (1.0 - (self.ripple_radius - 8.0) / 38.0)))
        if self.ripple_radius >= 46.0:
            self.ripple_radius = 8.0
            self.ripple_alpha = 240

        self.update()

    def paintEvent(self, event):
        if not self.instruction:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.cur_x, self.cur_y
        center_pt = QPointF(cx, cy)
        base_neon = QColor(LULU_THEME_HEX)
        hot_core = QColor(LULU_HOT_CORE_HEX)

        # 1. WIDE NEON AMBIENT BLOOM
        breath_scale = 42.0 + math.sin(self.phase) * 6.0
        ambient_grad = QRadialGradient(center_pt, breath_scale)
        c_inner = QColor(base_neon); c_inner.setAlpha(180)
        c_mid = QColor(base_neon); c_mid.setAlpha(75)
        c_outer = QColor(base_neon); c_outer.setAlpha(0)
        ambient_grad.setColorAt(0.0, c_inner)
        ambient_grad.setColorAt(0.45, c_mid)
        ambient_grad.setColorAt(1.0, c_outer)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ambient_grad)
        painter.drawEllipse(center_pt, breath_scale, breath_scale)

        # 2. EXPANDING SONAR RIPPLE RING
        if self.ripple_alpha > 5:
            ripple_color = QColor(base_neon)
            ripple_color.setAlpha(self.ripple_alpha)
            painter.setPen(QPen(ripple_color, 2.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center_pt, self.ripple_radius, self.ripple_radius)

        # 3. INTENSE HOT-CORE NEON ORB
        core_grad = QRadialGradient(center_pt, 14.0)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        core_grad.setColorAt(0.35, hot_core)
        core_grad.setColorAt(0.75, base_neon)
        core_grad.setColorAt(1.0, QColor(base_neon.red(), base_neon.green(), base_neon.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(core_grad)
        painter.drawEllipse(center_pt, 14.0, 14.0)

        painter.setPen(QPen(QColor(255, 230, 245, 230), 1.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center_pt, 7.5, 7.5)

        # 4. GLOWING POINTER ARROW TIP
        arrow = QPolygonF([
            QPointF(cx, cy),
            QPointF(cx + 6, cy + 20),
            QPointF(cx + 11, cy + 14),
            QPointF(cx + 19, cy + 12)
        ])
        painter.setPen(QPen(base_neon, 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPolygon(arrow)
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        painter.setBrush(base_neon)
        painter.drawPolygon(arrow)

        # 5. NEON GLASSMORPHISM FLOATING PILL BADGE
        box_x, box_y, box_w, box_h = cx + 28.0, cy - 22.0, 480.0, 44.0
        pill_rect = QRectF(box_x, box_y, box_w, box_h)

        # Outer subtle glow
        for i in range(3, 0, -1):
            glow_b = QColor(base_neon); glow_b.setAlpha(35 * i)
            painter.setPen(QPen(glow_b, i * 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(pill_rect, 12.0, 12.0)

        # Background Gradient
        bg_grad = QLinearGradient(box_x, box_y, box_x, box_y + box_h)
        bg_grad.setColorAt(0.0, QColor(24, 14, 32, 240))
        bg_grad.setColorAt(1.0, QColor(12, 8, 18, 245))
        painter.setBrush(bg_grad)
        painter.setPen(QPen(base_neon, 1.8))
        painter.drawRoundedRect(pill_rect, 12.0, 12.0)

        # Dual Status Light Dot (Online Indicator)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(base_neon)
        painter.drawEllipse(QPointF(box_x + 16.0, box_y + 22.0), 4.5, 4.5)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QPointF(box_x + 16.0, box_y + 22.0), 2.0, 2.0)

        # Text with Workflow context
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        display_text = f"Lulu: {self.instruction}"
        painter.drawText(int(box_x + 30), int(box_y + 27), display_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    lulu_hud = LuluOverlay()
    sys.exit(app.exec())