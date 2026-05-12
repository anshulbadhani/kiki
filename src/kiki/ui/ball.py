from __future__ import annotations
import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve,
    pyqtProperty, QRectF
)
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen

from ..config import (
    BALL_SIZE, BALL_OPACITY, BALL_DEFAULT_X, BALL_DEFAULT_Y,
    ANIMATION_TICK_MS, MOOD_TICK_MS,
)
from ..fsm.mood import MoodFSM
from ..fsm.mode import ModeFSM


# ---------------------------------------------------------------------------
# BallWidget
# ---------------------------------------------------------------------------

MOOD_COLORS = {
    "Calm":       QColor(80,  140, 220),   # cool blue
    "Annoyed":    QColor(220, 100,  70),   # coral-red
    "Grumpy":     QColor(180,  50,  50),   # deep red
    "Recovering": QColor(80,  180, 160),   # teal
    "Idle":       QColor(120, 120, 120),   # gray
}


class BallWidget(QWidget):
    """
    Frameless, translucent orb that lives on screen.
    Owns both FSMs and drives them.
    """

    def __init__(self) -> None:
        super().__init__()
        if hasattr(Qt, 'HANDLE'):
            pass  # placeholder
        
        
        # --- FSMs ---
        self.mood = MoodFSM()
        self.mode = ModeFSM(mood_fsm=self.mood)

        # --- window flags ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool               | # no taskbar entry
            Qt.WindowType.X11BypassWindowManagerHint
        )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(BALL_SIZE * 3, BALL_SIZE * 3)  # extra room for glow

        # --- position: bottom-left by default ---
        screen = QApplication.primaryScreen().geometry()
        x = BALL_DEFAULT_X
        y = screen.height() + BALL_DEFAULT_Y - self.height()
        self.move(x, y)

        # --- animation state ---
        self._scale: float = 1.0        # 0.0–1.5, painted size
        self._wobble: float = 0.0       # radians, horizontal wobble offset
        self._wobble_tick: int = 0
        self._shake_ticks: int = 0

        # --- harassment tracking ---
        self._enter_times: list[float] = []   # timestamps of recent enters
        self._harassment_window_ms = 1500     # rolling window
        self._harassment_enter_threshold = 4  # enters in window = harass

        # --- drag state ---
        self._drag_origin: QPoint | None = None
        self._drag_moved: bool = False

        # --- timers ---
        self._mood_timer = QTimer(self)
        self._mood_timer.timeout.connect(self._on_mood_tick)
        self._mood_timer.start(MOOD_TICK_MS)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start(ANIMATION_TICK_MS)

        self.setMouseTracking(True)

    # -----------------------------------------------------------------------
    # Ticks
    # -----------------------------------------------------------------------

    def _on_mood_tick(self) -> None:
        self.mood.tick(MOOD_TICK_MS)
        self.update()   # repaint on every mood tick

    def _on_anim_tick(self) -> None:
        m = self.mood.mood

        # wobble: always present, faster when annoyed/grumpy
        speed = {"Calm": 0.04, "Recovering": 0.04,
                 "Annoyed": 0.10, "Grumpy": 0.13, "Idle": 0.01}
        self._wobble_tick += 1
        self._wobble = math.sin(self._wobble_tick * speed.get(m, 0.05)) * (
            3 if m == "Calm" else 6 if m == "Annoyed" else 9
        )

        # shake: triggered by harass(), counts down
        if self._shake_ticks > 0:
            self._shake_ticks -= 1
            self._wobble += math.sin(self._wobble_tick * 0.8) * 12

        # scale: grumpy = shrink, annoyed = swell
        target_scale = {
            "Calm": 1.0, "Recovering": 1.0,
            "Annoyed": 1.08, "Grumpy": 0.88, "Idle": 0.75
        }.get(m, 1.0)
        self._scale += (target_scale - self._scale) * 0.12  # lerp

        self.update()

    # -----------------------------------------------------------------------
    # Painting
    # -----------------------------------------------------------------------

    def paintEvent(self, _) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2 + self._wobble
        cy = self.height() / 2
        r = (BALL_SIZE / 2) * self._scale

        mood = self.mood.mood
        base_color = MOOD_COLORS.get(mood, MOOD_COLORS["Calm"])

        # --- glow ---
        glow = QRadialGradient(cx, cy, r * 2.2)
        glow_color = QColor(base_color)
        glow_color.setAlpha(40)
        glow.setColorAt(0.0, glow_color)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - r * 2.2, cy - r * 2.2, r * 4.4, r * 4.4))

        # --- body ---
        body = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.2)
        body_color = QColor(base_color)
        body_color.setAlpha(int(255 * BALL_OPACITY))
        highlight = QColor(255, 255, 255, 80)
        body.setColorAt(0.0, highlight)
        body.setColorAt(0.4, body_color)
        body.setColorAt(1.0, body_color.darker(140))
        painter.setBrush(body)
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        painter.end()

    # -----------------------------------------------------------------------
    # Mouse events
    # -----------------------------------------------------------------------

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = e.globalPosition().toPoint()
            self._drag_moved = False
            self.mode.mouse_down()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_origin is not None:
            delta = e.globalPosition().toPoint() - self._drag_origin
            if delta.manhattanLength() > 4:
                self._drag_moved = True
            if self._drag_moved and self.mode.mode == "Dragging":
                self.move(self.pos() + delta)
                self._drag_origin = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if not self._drag_moved:
                self.mode.mouse_up()
                self.mode.click()    # was a tap, not a drag
            else:
                self.mode.mouse_up()
            self._drag_origin = None
            self._drag_moved = False

    def enterEvent(self, e) -> None:
        """Track rapid cursor entries as harassment."""
        import time
        now = time.monotonic() * 1000
        self._enter_times.append(now)
        # prune old entries outside window
        self._enter_times = [
            t for t in self._enter_times
            if now - t <= self._harassment_window_ms
        ]
        if len(self._enter_times) >= self._harassment_enter_threshold:
            self.mood.harass()
            self._shake_ticks = 8
            self._enter_times.clear()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _screen_bottom_left(self) -> QPoint:
        screen = QApplication.primaryScreen().geometry()
        return QPoint(
            BALL_DEFAULT_X,
            screen.height() + BALL_DEFAULT_Y - self.height()
        )
        
    def force_always_on_top(self) -> None:
        """Force always-on-top via X11 atoms — needed for WSLg/XWayland."""
        try:
            from Xlib import display, X
            from Xlib.protocol import event

            d = display.Display()
            root = d.screen().root
            win = d.create_resource_object('window', int(self.winId()))

            _NET_WM_STATE = d.intern_atom('_NET_WM_STATE')
            _NET_WM_STATE_ABOVE = d.intern_atom('_NET_WM_STATE_ABOVE')

            ev = event.ClientMessage(
                window=win,
                client_type=_NET_WM_STATE,
                data=(32, [1, _NET_WM_STATE_ABOVE, 0, 1, 0])
            )
            mask = X.SubstructureRedirectMask | X.SubstructureNotifyMask
            root.send_event(ev, event_mask=mask)
            d.flush()
        except Exception as e:
            print(f"force_always_on_top failed: {e}")