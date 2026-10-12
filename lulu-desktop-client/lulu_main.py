import sys
import time
import math
import ctypes

# LOCK WINDOWS DPI SCALING SO PYWINAUTO AND PYQT6 PIXELS MATCH 100%
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QPoint
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QRadialGradient, 
    QLinearGradient, QPen, QPolygonF, QGuiApplication
)
from lulu_voice import LuluVoiceEngine
from ui_scanner import LuluUIScanner

LULU_THEME_HEX = "#fc038c"
LULU_HOT_CORE_HEX = "#ff99d6"

SAMPLE_WORKFLOW = {
    "window_title": "Enterprise Billing Portal",
    "steps": [
        {
            "step_num": 1,
            "target_button": "Open Customer Invoices",
            "badge_text": "Step 1: Click 'Open Customer Invoices'",
            "voice_text": "Welcome! Step 1: Click Open Customer Invoices.",
            "verify_screen_text": "Open Customer Invoices (Done)"
        },
        {
            "step_num": 2,
            "target_button": "Verify Account Balance",
            "badge_text": "Step 2: Click 'Verify Account Balance'",
            "voice_text": "Great! Step 2: Click Verify Account Balance.",
            "verify_screen_text": "Verify Account Balance (Done)"
        },
        {
            "step_num": 3,
            "target_button": "Approve & Issue Refund",
            "badge_text": "Step 3: Click 'Approve & Issue Refund'",
            "voice_text": "Almost done! Step 3: Click Approve and Issue Refund.",
            "verify_screen_text": "Approve & Issue Refund (Done)"
        }
    ]
}

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
        self.instruction = "Scanning for Enterprise Billing Portal..."
        
        self.phase = 0.0
        self.ripple_radius = 10.0
        self.ripple_alpha = 220

        self.steps = SAMPLE_WORKFLOW["steps"]
        self.current_step_idx = 0
        self.step_start_time = time.time()
        self.spoken_current_step = False
        self.telemetry_results = []
        self.workflow_finished = False

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate_lulu)
        self.anim_timer.start(16)

        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.update_fsm_and_scan)
        self.scan_timer.start(350)

    def physical_to_logical(self, phys_x, phys_y):
        """Converts raw Windows physical pixels into exact PyQt6 screen coordinates."""
        screen = QGuiApplication.screenAt(QPoint(int(phys_x), int(phys_y)))
        if not screen:
            screen = QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio()
        local_pos = self.mapFromGlobal(QPoint(int(phys_x / dpr), int(phys_y / dpr)))
        return float(local_pos.x()), float(local_pos.y())

    def update_fsm_and_scan(self):
        if self.workflow_finished:
            return

        elements = self.scanner.scan_window(SAMPLE_WORKFLOW["window_title"])
        if not elements:
            self.instruction = "Waiting for 'Enterprise Billing Portal' window..."
            return

        current_step = self.steps[self.current_step_idx]

        # 1. Check if current step button was clicked and marked (Done)
        if self.scanner.is_text_on_screen(elements, current_step["verify_screen_text"]):
            duration = round(time.time() - self.step_start_time, 1)
            self.telemetry_results.append(f"Step {current_step['step_num']}: {duration}s")
            print(f"[Lulu Telemetry] Step {current_step['step_num']} completed in {duration}s")

            self.current_step_idx += 1
            self.step_start_time = time.time()
            self.spoken_current_step = False

            if self.current_step_idx >= len(self.steps):
                self.workflow_finished = True
                summary = " | ".join(self.telemetry_results)
                self.instruction = f"🎉 Complete! Times: {summary}"
                self.voice.speak("Awesome job! You have completed the entire onboarding workflow.")
                return

            current_step = self.steps[self.current_step_idx]

        # 2. Locate exact button center and adjust for laptop DPI scaling
        coords = self.scanner.find_element_center(elements, current_step["target_button"])
        if coords:
            lx, ly = self.physical_to_logical(coords[0], coords[1])
            self.target_x, self.target_y = lx, ly
            self.instruction = current_step["badge_text"]

            if not self.spoken_current_step:
                self.voice.speak(current_step["voice_text"])
                self.spoken_current_step = True

    def animate_lulu(self):
        self.cur_x += (self.target_x - self.cur_x) * 0.22
        self.cur_y += (self.target_y - self.cur_y) * 0.22
        self.phase += 0.08

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
        box_x, box_y, box_w, box_h = cx + 28.0, cy - 22.0, 430.0, 42.0
        pill_rect = QRectF(box_x, box_y, box_w, box_h)

        for i in range(3, 0, -1):
            glow_b = QColor(base_neon); glow_b.setAlpha(35 * i)
            painter.setPen(QPen(glow_b, i * 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(pill_rect, 12.0, 12.0)

        bg_grad = QLinearGradient(box_x, box_y, box_x, box_y + box_h)
        bg_grad.setColorAt(0.0, QColor(24, 14, 32, 240))
        bg_grad.setColorAt(1.0, QColor(12, 8, 18, 245))
        painter.setBrush(bg_grad)
        painter.setPen(QPen(base_neon, 1.8))
        painter.drawRoundedRect(pill_rect, 12.0, 12.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(base_neon)
        painter.drawEllipse(QPointF(box_x + 16.0, box_y + 21.0), 4.5, 4.5)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QPointF(box_x + 16.0, box_y + 21.0), 2.0, 2.0)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(int(box_x + 30), int(box_y + 26), f"Lulu: {self.instruction}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    lulu_hud = LuluOverlay()
    sys.exit(app.exec())