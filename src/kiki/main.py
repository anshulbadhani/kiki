from __future__ import annotations
import sys
from PyQt6.QtWidgets import QApplication
from kiki.brain import Brain
from kiki.ui.ball import BallWidget


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    brain = Brain()
    ball  = BallWidget(brain=brain)
    ball.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()