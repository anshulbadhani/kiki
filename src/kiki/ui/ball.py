from __future__ import annotations
import sys
import math
import time

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient

from ..config import (
    BALL_SIZE, BALL_OPACITY, BALL_DEFAULT_X, BALL_DEFAULT_Y,
    ANIMATION_TICK_MS, MOOD_TICK_MS,
)
from ..fsm.mood import MoodFSM
from ..fsm.mode import ModeFSM


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MOOD_COLORS: dict[str, QColor] = {
    "Calm":       QColor(80,  140, 220),
    "Annoyed":    QColor(220, 100,  70),
    "Grumpy":     QColor(180,  50,  50),
    "Recovering": QColor(80,  180, 160),
    "Idle":       QColor(120, 120, 120),
}

WOBBLE_SPEED: dict[str, float] = {
    "Calm": 0.04, "Recovering": 0.04,
    "Annoyed": 0.10, "Grumpy": 0.13, "Idle": 0.01,
}

WOBBLE_AMP: dict[str, float] = {
    "Calm": 3.0, "Recovering": 3.0,
    "Annoyed": 6.0, "Grumpy": 9.0, "Idle": 1.0,
}

TARGET_SCALE: dict[str, float] = {
    "Calm": 1.0, "Recovering": 1.0,
    "Annoyed": 1.08, "Grumpy": 0.88, "Idle": 0.75,
}


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------

def _apply_window_flags(widget: QWidget) -> None:
    """Set frameless, always-on-top, no-taskbar flags cross-platform."""
    flags = (
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.Tool
    )
    if sys.platform == "linux":
        # X11BypassWindowManagerHint needed on some compositors
        flags |= Qt.WindowType.X11BypassWindowManagerHint
    widget.setWindowFlags(flags)


def _apply_translucency(widget: QWidget) -> None:
    """Enable per-pixel alpha transparency cross-platform."""
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    widget.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)


def _fix_transparency_after_show(widget: QWidget) -> None:
    """
    Post-show platform fixes.
    Windows: extend DWM frame to full client area for true transparency.
    Linux:   send _NET_WM_STATE_ABOVE atom for compositors that ignore the Qt hint.
    """
    if sys.platform == "win32":
        _dwm_extend_frame(widget)
    elif sys.platform == "linux":
        _x11_force_above(widget)


def _dwm_extend_frame(widget: QWidget) -> None:
    try:
        import ctypes
        margins = (ctypes.c_int * 4)(-1, -1, -1, -1)
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
            int(widget.winId()), ctypes.byref(margins)
        )
    except Exception as e:
        print(f"[kiki] DwmExtendFrameIntoClientArea failed: {e}")


def _x11_force_above(widget: QWidget) -> None:
    try:
        from Xlib import display, X
        from Xlib.protocol import event as xevent

        d = display.Display()
        root = d.screen().root
        win = d.create_resource_object("window", int(widget.winId()))
        _NET_WM_STATE       = d.intern_atom("_NET_WM_STATE")
        _NET_WM_STATE_ABOVE = d.intern_atom("_NET_WM_STATE_ABOVE")
        ev = xevent.ClientMessage(
            window=win,
            client_type=_NET_WM_STATE,
            data=(32, [1, _NET_WM_STATE_ABOVE, 0, 1, 0]),
        )
        root.send_event(ev, event_mask=(
            X.SubstructureRedirectMask | X.SubstructureNotifyMask
        ))
        d.flush()
    except Exception as e:
        print(f"[kiki] X11 force-above failed: {e}")


# ---------------------------------------------------------------------------
# Animation state  (pure data, no Qt dependency)
# ---------------------------------------------------------------------------

class _AnimState:
    """Holds all transient animation values, updated every ANIMATION_TICK_MS."""

    def __init__(self) -> None:
        self.scale:       float = 1.0
        self.wobble:      float = 0.0
        self._tick:       int   = 0
        self._shake_left: int   = 0

    def trigger_shake(self, ticks: int = 10) -> None:
        self._shake_left = ticks

    def update(self, mood: str) -> None:
        self._tick += 1
        speed = WOBBLE_SPEED.get(mood, 0.05)
        amp   = WOBBLE_AMP.get(mood, 3.0)
        self.wobble = math.sin(self._tick * speed) * amp

        if self._shake_left > 0:
            self._shake_left -= 1
            self.wobble += math.sin(self._tick * 0.8) * 12

        target = TARGET_SCALE.get(mood, 1.0)
        self.scale += (target - self.scale) * 0.12   # lerp toward target


# ---------------------------------------------------------------------------
# Harassment tracker  (pure data, no Qt dependency)
# ---------------------------------------------------------------------------

class _HarassmentTracker:
    """
    Counts cursor enter events in a rolling time window.
    Avoids 24/7 mouse polling — purely event-driven.
    """

    def __init__(
        self,
        window_ms: float = 1500,
        threshold: int   = 4,
    ) -> None:
        self._window_ms  = window_ms
        self._threshold  = threshold
        self._timestamps: list[float] = []

    def record_enter(self) -> bool:
        """Call on every enterEvent. Returns True if harassment threshold hit."""
        now = time.monotonic() * 1000
        self._timestamps.append(now)
        self._timestamps = [
            t for t in self._timestamps if now - t <= self._window_ms
        ]
        if len(self._timestamps) >= self._threshold:
            self._timestamps.clear()
            return True
        return False


# ---------------------------------------------------------------------------
# BallWidget
# ---------------------------------------------------------------------------

class BallWidget(QWidget):
    """
    Frameless translucent orb.  Owns both FSMs and drives them.
    Platform differences are handled internally — callers need not care.
    """

    def __init__(self) -> None:
        super().__init__()

        # FSMs
        self.mood = MoodFSM()
        self.mode = ModeFSM(mood_fsm=self.mood)

        # Platform window setup
        _apply_window_flags(self)
        _apply_translucency(self)

        # Size — extra padding so the glow has room
        self.setFixedSize(BALL_SIZE * 3, BALL_SIZE * 3)

        # Default position: bottom-left
        self._move_to_default()

        # Sub-objects
        self._anim       = _AnimState()
        self._harassment = _HarassmentTracker()

        # Drag state
        self._drag_origin: QPoint | None = None
        self._drag_moved:  bool          = False

        # Timers
        self._mood_timer = QTimer(self)
        self._mood_timer.timeout.connect(self._on_mood_tick)
        self._mood_timer.start(MOOD_TICK_MS)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start(ANIMATION_TICK_MS)

        self.setMouseTracking(True)

    # -----------------------------------------------------------------------
    # Qt lifecycle
    # -----------------------------------------------------------------------

    def showEvent(self, e) -> None:
        super().showEvent(e)
        _fix_transparency_after_show(self)

    # -----------------------------------------------------------------------
    # Timer slots
    # -----------------------------------------------------------------------

    def _on_mood_tick(self) -> None:
        self.mood.tick(MOOD_TICK_MS)
        self.update()

    def _on_anim_tick(self) -> None:
        self._anim.update(self.mood.mood)
        self.update()

    # -----------------------------------------------------------------------
    # Painting
    # -----------------------------------------------------------------------

    def paintEvent(self, _) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width()  / 2 + self._anim.wobble
        cy = self.height() / 2
        r  = (BALL_SIZE / 2) * self._anim.scale

        base = MOOD_COLORS.get(self.mood.mood, MOOD_COLORS["Calm"])

        self._paint_glow(painter, cx, cy, r, base)
        self._paint_body(painter, cx, cy, r, base)

        painter.end()

    def _paint_glow(
        self, p: QPainter, cx: float, cy: float, r: float, base: QColor
    ) -> None:
        grad = QRadialGradient(cx, cy, r * 2.2)
        glow = QColor(base)
        glow.setAlpha(40)
        grad.setColorAt(0.0, glow)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r * 2.2, cy - r * 2.2, r * 4.4, r * 4.4))

    def _paint_body(
        self, p: QPainter, cx: float, cy: float, r: float, base: QColor
    ) -> None:
        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.2)
        body = QColor(base)
        body.setAlpha(int(255 * BALL_OPACITY))
        grad.setColorAt(0.0, QColor(255, 255, 255, 80))
        grad.setColorAt(0.4, body)
        grad.setColorAt(1.0, body.darker(140))
        p.setBrush(grad)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

    # -----------------------------------------------------------------------
    # Mouse events
    # -----------------------------------------------------------------------

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = e.globalPosition().toPoint()
            self._drag_moved  = False
            self.mode.mouse_down()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_origin is None:
            return
        delta = e.globalPosition().toPoint() - self._drag_origin
        if delta.manhattanLength() > 4:
            self._drag_moved = True
        if self._drag_moved and self.mode.mode == "Dragging":
            self.move(self.pos() + delta)
            self._drag_origin = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if not self._drag_moved:
            self.mode.mouse_up()
            self.mode.click()
        else:
            self.mode.mouse_up()
        self._drag_origin = None
        self._drag_moved  = False

    def enterEvent(self, e) -> None:
        if self._harassment.record_enter():
            self.mood.harass()
            self._anim.trigger_shake()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _move_to_default(self) -> None:
        screen = QApplication.primaryScreen().geometry()
        self.move(
            BALL_DEFAULT_X,
            screen.height() + BALL_DEFAULT_Y - self.height(),
        )