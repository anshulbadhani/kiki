from __future__ import annotations
import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox
from kiki.paths import kiki_home


def _get_secrets_file() -> Path:
    """Get the path to the persistent secrets file in Kiki's home dir."""
    return kiki_home() / "secrets.json"


def ensure_api_key(app: QApplication) -> None:
    """Check for API key. If missing, show a clean PyQt dialog to the user."""
    
    # FIX 2: Load the .env file BEFORE checking the environment!
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass # It's fine if this fails in the final .exe

    secrets_file = _get_secrets_file()

    # 1. Check if the user already saved it in a previous session
    if secrets_file.exists():
        try:
            with open(secrets_file, "r") as f:
                secrets = json.load(f)
                if "GROQ_API_KEY" in secrets:
                    os.environ["GROQ_API_KEY"] = secrets["GROQ_API_KEY"]
                    return
        except json.JSONDecodeError:
            pass

    # 2. Check for Dev environment (.env)
    if os.getenv("GROQ_API_KEY"):
        return

    # 3. First-run experience: Prompt the user
    key, ok = QInputDialog.getText(
        None, 
        "Welcome to Kiki!", 
        "Please enter your Groq API Key to wake Kiki up.\n(You can get one for free at console.groq.com):"
    )

    if ok and key.strip():
        with open(secrets_file, "w") as f:
            json.dump({"GROQ_API_KEY": key.strip()}, f)
        os.environ["GROQ_API_KEY"] = key.strip()
    else:
        QMessageBox.warning(None, "Key Required", "Kiki needs a Groq API key to function. See you later!")
        sys.exit(0)


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # MUST run before importing Brain! This ensures os.environ is populated
    # so your config.py picks it up seamlessly via os.getenv()
    ensure_api_key(app)

    # Deferred imports so config.py loads *after* we check the API key
    from kiki.brain import Brain
    from kiki.ui.ball import BallWidget

    brain = Brain()
    ball  = BallWidget(brain=brain)
    ball.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()