"""
Skill: open_app
Opens an application by name. Cross-platform.
"""
from __future__ import annotations
import sys
import subprocess

NAME        = "open_app"
DESCRIPTION = "open launch start run an application program software"
EXAMPLES    = [
    "open chrome",
    "launch spotify",
    "start notepad",
    "open calculator",
    "run vlc",
    "launch file explorer",
    "open terminal",
    "start visual studio code",
]
PARAMETERS      = {"query": "full user message to extract app name from"}
REQUIRES_VISION = False

# ---------------------------------------------------------------------------
# App name aliases — common names → actual executable / app
# ---------------------------------------------------------------------------

ALIASES: dict[str, str] = {
    # Windows
    "chrome":        "chrome",
    "google chrome": "chrome",
    "firefox":       "firefox",
    "edge":          "msedge",
    "notepad":       "notepad",
    "calculator":    "calc",
    "explorer":      "explorer",
    "file explorer": "explorer",
    "terminal":      "wt",          # windows terminal
    "cmd":           "cmd",
    "powershell":    "powershell",
    "vscode":        "code",
    "visual studio code": "code",
    "spotify":       "spotify",
    "vlc":           "vlc",
    "paint":         "mspaint",
    "word":          "winword",
    "excel":         "excel",
    "slack":         "slack",
    "discord":       "discord",
    "obs":           "obs64",
    # macOS
    "finder":        "Finder",
    "safari":        "Safari",
    "xcode":         "Xcode",
    # Linux
    "files":         "nautilus",
    "gedit":         "gedit",
}

TRIGGER_WORDS = {"open", "launch", "start", "run", "fire up", "bring up"}


def _extract_app(message: str) -> str | None:
    """Extract app name from message by stripping trigger words."""
    msg = message.lower().strip()
    for trigger in sorted(TRIGGER_WORDS, key=len, reverse=True):
        if msg.startswith(trigger):
            return msg[len(trigger):].strip()
    return msg


def _resolve(app: str) -> str:
    """Resolve alias if known, otherwise use as-is."""
    return ALIASES.get(app.lower(), app)


def _launch(executable: str) -> None:
    if sys.platform == "win32":
        subprocess.Popen(
            ["cmd", "/c", "start", "", executable],
            shell=False,
            creationflags=subprocess.DETACHED_PROCESS,
        )
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-a", executable])
    else:
        subprocess.Popen(
            [executable],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def run(query: str = "", **kwargs) -> str:
    app_raw  = _extract_app(query)
    if not app_raw:
        return "what do you want me to open?"

    app_name = _resolve(app_raw)

    try:
        _launch(app_name)
        return f"opening {app_raw}."
    except FileNotFoundError:
        return f"couldn't find {app_raw}."
    except Exception as e:
        return f"failed to open {app_raw}: {e}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    assert _extract_app("open chrome")        == "chrome"
    assert _extract_app("launch spotify")     == "spotify"
    assert _extract_app("start notepad")      == "notepad"
    assert _extract_app("fire up vlc")        == "vlc"
    assert _resolve("chrome")                 == "chrome"
    assert _resolve("visual studio code")     == "code"
    assert _resolve("calculator")             == "calc"

    print("open_app.py — all tests passed.")
    print("(skipping actual launch in test mode)")