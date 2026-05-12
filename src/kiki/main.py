from __future__ import annotations
import sys
from PyQt6.QtWidgets import QApplication
from kiki.ui.ball import BallWidget


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    ball = BallWidget()
    ball.show()
    # ball.raise_()
    # ball.activateWindow()
    # ball.force_always_on_top()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()