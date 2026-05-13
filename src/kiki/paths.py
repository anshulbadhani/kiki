import sys
import os
from pathlib import Path

def kiki_home() -> Path:
    """
    Platform-specific Kiki data directory.
    Windows : C:/Users/<user>/AppData/Local/kiki
    macOS   : ~/Library/Application Support/kiki
    Linux   : ~/.local/share/kiki
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    path = base / "kiki"
    path.mkdir(parents=True, exist_ok=True)
    return path

def user_skills_dir() -> Path:
    """Where users can drop their custom .py skill files."""
    path = kiki_home() / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path
