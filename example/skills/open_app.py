from __future__ import annotations
import sys
import subprocess
from dataclasses import dataclass, field
from kiki.skills.base import Skill


ALIASES: dict[str, str] = {
    "chrome":             "chrome",
    "google chrome":      "chrome",
    "edge":               "msedge",
    "notepad":            "notepad",
    "calculator":         "calc",
    "explorer":           "explorer",
    "file explorer":      "explorer",
    "terminal":           "wt",
    "cmd":                "cmd",
    "powershell":         "powershell",
    "vscode":             "code",
    "visual studio code": "code",
    "spotify":            "spotify",
    "vlc":                "vlc",
    "paint":              "mspaint",
    "word":               "winword",
    "excel":              "excel",
    "slack":              "slack",
    "discord":            "discord",
    "obs":                "obs64",
    "finder":             "Finder",
    "safari":             "Safari",
    "files":              "nautilus",
}

TRIGGER_WORDS = {"open", "launch", "start", "run", "fire up", "bring up"}


@dataclass
class OpenAppSkill(Skill):
    name:        str       = "open_app"
    description: str       = "open launch start run an application program software"
    examples:    list[str] = field(default_factory=lambda: [
        "open chrome",
        "launch spotify",
        "start notepad",
        "open calculator",
        "run vlc",
        "launch file explorer",
        "open terminal",
        "start visual studio code",
    ])
    category:    str       = "system"
    parameters:  dict      = field(default_factory=lambda: {
        "query": "full user message to extract app name from"
    })

    def run(self, query: str = "", **kwargs) -> str:
        app_raw = self._extract_app(query)
        if not app_raw:
            return "what do you want me to open?"
        app_name = self._resolve(app_raw)
        try:
            self._launch(app_name)
            return f"opening {app_raw}."
        except FileNotFoundError:
            return f"couldn't find {app_raw}."
        except Exception as e:
            return f"failed to open {app_raw}: {e}"

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _extract_app(self, message: str) -> str | None:
        msg = message.lower().strip()
        for trigger in sorted(TRIGGER_WORDS, key=len, reverse=True):
            if msg.startswith(trigger):
                return msg[len(trigger):].strip()
        return msg

    def _resolve(self, app: str) -> str:
        return ALIASES.get(app.lower(), app)

    def _launch(self, executable: str) -> None:
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    skill = OpenAppSkill()
    assert skill._extract_app("open chrome")    == "chrome"
    assert skill._extract_app("launch spotify") == "spotify"
    assert skill._extract_app("start notepad")  == "notepad"
    assert skill._extract_app("fire up vlc")    == "vlc"
    assert skill._resolve("chrome")             == "chrome"
    assert skill._resolve("visual studio code") == "code"
    assert skill._resolve("calculator")         == "calc"
    assert skill.corpus.startswith("open launch start")
    print("open_app.py — all tests passed.")
