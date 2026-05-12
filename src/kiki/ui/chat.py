from __future__ import annotations
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont

from ..config import (
    CHAT_WIDTH, CHAT_HEIGHT, CHAT_MARGIN,
    KIKI_NAME, BALL_SIZE,
)


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

BG          = QColor(14,  14,  14)
BG_MSG      = QColor(24,  24,  24)
BG_USER     = QColor(30,  30,  40)
BG_INPUT    = QColor(20,  20,  20)
TEXT_MAIN   = QColor(220, 220, 220)
TEXT_DIM    = QColor(100, 100, 100)
TEXT_USER   = QColor(160, 160, 200)
BORDER      = QColor(40,  40,  40)
ACCENT      = QColor(80,  140, 220)   # calm blue — matches ball


# ---------------------------------------------------------------------------
# MessageBubble
# ---------------------------------------------------------------------------

class MessageBubble(QLabel):
    """A single chat message — kiki or user."""

    def __init__(self, text: str, is_user: bool = False) -> None:
        super().__init__(text)
        self.is_user = is_user
        self.setWordWrap(True)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        font = QFont("Consolas", 10) if sys.platform == "win32" \
               else QFont("Monospace", 10)
        self.setFont(font)

        color     = TEXT_USER.name() if is_user else TEXT_MAIN.name()
        bg        = BG_USER.name()   if is_user else BG_MSG.name()
        align     = "right"          if is_user else "left"

        self.setStyleSheet(f"""
            QLabel {{
                color:            {color};
                background-color: {bg};
                border-radius:    6px;
                padding:          6px 10px;
            }}
        """)
        self.setAlignment(
            Qt.AlignmentFlag.AlignRight if is_user
            else Qt.AlignmentFlag.AlignLeft
        )
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )

    def append_token(self, token: str) -> None:
        print(f"[bubble] append_token called: {token!r}, current: {self.text()!r}")
        self.setText(self.text() + token)
        self.adjustSize()          # recompute height as text grows
        self.updateGeometry()   
        self.repaint()   


# ---------------------------------------------------------------------------
# ChatPanel
# ---------------------------------------------------------------------------

class ChatPanel(QWidget):
    """
    Frameless dark chat panel.
    Emits:
        message_submitted(str)  — user hit enter or send
        close_requested()       — user clicked ×
    """

    message_submitted = pyqtSignal(str)
    close_requested   = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._drag_pos: QPoint | None = None

        self._setup_window()
        self._build_ui()

    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(CHAT_WIDTH, CHAT_HEIGHT)
        self._move_to_default()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- container with rounded corners ---------------------------------
        self._container = QWidget()
        self._container.setObjectName("container")
        self._container.setStyleSheet(f"""
            QWidget#container {{
                background-color: {BG.name()};
                border-radius:    12px;
                border:           0.5px solid {BORDER.name()};
            }}
        """)
        root.addWidget(self._container)

        inner = QVBoxLayout(self._container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        inner.addWidget(self._build_header())
        inner.addWidget(self._build_scroll(), stretch=1)
        inner.addWidget(self._build_input_bar())

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(42)
        header.setStyleSheet(f"""
            background-color: {BG.name()};
            border-bottom: 0.5px solid {BORDER.name()};
            border-top-left-radius:  12px;
            border-top-right-radius: 12px;
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 0, 12, 0)

        # mini orb avatar
        self._avatar = _MiniOrb()
        layout.addWidget(self._avatar)

        # name
        name_lbl = QLabel(KIKI_NAME)
        name_lbl.setStyleSheet(f"""
            color: {TEXT_DIM.name()};
            font-family: Consolas, Monospace;
            font-size: 12px;
        """)
        layout.addWidget(name_lbl)
        layout.addStretch()

        # close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color:            {TEXT_DIM.name()};
                background:       transparent;
                border:           none;
                font-size:        18px;
                padding:          0;
            }}
            QPushButton:hover {{
                color: {TEXT_MAIN.name()};
            }}
        """)
        close_btn.clicked.connect(self.close_requested.emit)
        layout.addWidget(close_btn)

        return header

    def _build_scroll(self) -> QScrollArea:
        # self._msg_layout.setContentsMargins(10, 10, 10, 10)
        # self._msg_layout.setSpacing(6)
        # self._msg_layout.addStretch()
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border:     none;
            }}
            QScrollBar:vertical {{
                background: {BG.name()};
                width:      4px;
            }}
            QScrollBar::handle:vertical {{
                background:    {BORDER.name()};
                border-radius: 2px;
                min-height:    20px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self._msg_container = QWidget()
        self._msg_container.setStyleSheet("background: transparent;")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(10, 10, 10, 10)
        self._msg_layout.setSpacing(6)
        self._msg_layout.addStretch()

        self._scroll.setWidget(self._msg_container)
        return self._scroll

    def _build_input_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"""
            background-color: {BG.name()};
            border-top: 0.5px solid {BORDER.name()};
            border-bottom-left-radius:  12px;
            border-bottom-right-radius: 12px;
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)

        self._input = QLineEdit()
        self._input.setPlaceholderText(f"ask {KIKI_NAME}...")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background:    {BG_INPUT.name()};
                color:         {TEXT_MAIN.name()};
                border:        0.5px solid {BORDER.name()};
                border-radius: 6px;
                padding:       4px 10px;
                font-family:   Consolas, Monospace;
                font-size:     11px;
            }}
            QLineEdit:focus {{
                border-color: {ACCENT.name()};
            }}
        """)
        self._input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._input)

        send_btn = QPushButton("↑")
        send_btn.setFixedSize(30, 30)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background:    {ACCENT.name()};
                color:         white;
                border:        none;
                border-radius: 6px;
                font-size:     16px;
            }}
            QPushButton:hover {{
                background: {ACCENT.lighter(120).name()};
            }}
        """)
        send_btn.clicked.connect(self._on_submit)
        layout.addWidget(send_btn)

        return bar

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def add_user_message(self, text: str) -> None:
        bubble = MessageBubble(text, is_user=True)
        self._msg_layout.insertWidget(
            self._msg_layout.count() - 1, bubble
        )
        bubble.show()
        self._scroll_to_bottom()

    def start_kiki_message(self) -> MessageBubble:
        """Add an empty kiki bubble and return it for token streaming."""
        print(f"[chat] start_kiki_message called, layout count: {self._msg_layout.count()}")
        bubble = MessageBubble("", is_user=False)   # cursor placeholder
        self._msg_layout.insertWidget(
            self._msg_layout.count() - 1, bubble
        )
        bubble.show()
        print(f"[chat] msg_container visible: {self._msg_container.isVisible()}")
        print(f"[chat] scroll visible: {self._scroll.isVisible()}")
        print(f"[chat] self visible: {self.isVisible()}")
        print(f"[chat] container visible: {self._container.isVisible()}")
        print(f"[chat] bubble added, layout count now: {self._msg_layout.count()}")
        print(f"[chat] bubble visible: {bubble.isVisible()}, size: {bubble.size()}")
        self._scroll_to_bottom()
        return bubble

    def set_thinking(self, thinking: bool) -> None:
        """Disable / enable input while kiki is thinking."""
        self._input.setEnabled(not thinking)
        self._input.setPlaceholderText(
            "..." if thinking else f"ask {KIKI_NAME}..."
        )

    def update_avatar_mood(self, mood: str) -> None:
        self._avatar.set_mood(mood)

    def focus_input(self) -> None:
        self._input.setFocus()

    # -----------------------------------------------------------------------
    # Drag to reposition
    # -----------------------------------------------------------------------

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e) -> None:
        self._drag_pos = None

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _on_submit(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.message_submitted.emit(text)

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(
            50, lambda: self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            )
        )

    def _move_to_default(self) -> None:
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - CHAT_WIDTH - CHAT_MARGIN
        y = (screen.height() - CHAT_HEIGHT) // 2
        self.move(x, y)


# ---------------------------------------------------------------------------
# Mini orb avatar (header)
# ---------------------------------------------------------------------------

class _MiniOrb(QWidget):
    """Tiny version of the ball used in the chat header."""

    MOOD_COLORS = {
        "Calm":       QColor(80,  140, 220),
        "Annoyed":    QColor(220, 100,  70),
        "Grumpy":     QColor(180,  50,  50),
        "Recovering": QColor(80,  180, 160),
        "Idle":       QColor(120, 120, 120),
    }

    def __init__(self) -> None:
        super().__init__()
        self._mood = "Calm"
        self.setFixedSize(16, 16)

    def set_mood(self, mood: str) -> None:
        self._mood = mood
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.MOOD_COLORS.get(self._mood, self.MOOD_COLORS["Calm"])
        from PyQt6.QtCore import QRectF
        from PyQt6.QtGui import QRadialGradient
        cx, cy, r = 8.0, 8.0, 7.0
        grad = QRadialGradient(cx - 2, cy - 2, r * 1.2)
        grad.setColorAt(0.0, QColor(255, 255, 255, 80))
        grad.setColorAt(0.5, color)
        grad.setColorAt(1.0, color.darker(140))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        p.end()