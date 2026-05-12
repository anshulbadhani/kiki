from __future__ import annotations
import sys
import re
import threading
import time
import subprocess
from dataclasses import dataclass, field

from .base import Skill
from ..config import KIKI_NAME


_TIME_PATTERN = re.compile(
    r"in\s+(\d+)\s*(second|seconds|sec|minute|minutes|min|hour|hours|hr)s?",
    re.IGNORECASE,
)


@dataclass
class NotifySkill(Skill):
    name:        str       = "notify"
    description: str       = "notify remind alert notification message popup"
    examples:    list[str] = field(default_factory=lambda: [
        "remind me to drink water",
        "send a notification",
        "notify me about the meeting",
        "set a reminder",
        "alert me in 5 minutes",
        "remind me to take a break",
        "send me a popup",
        "give me a reminder",
    ])
    category:   str  = "system"
    parameters: dict = field(default_factory=lambda: {
        "query": "full user message"
    })

    def run(self, query: str = "", **kwargs) -> str:
        msg   = self._extract_message(query)
        delay = self._parse_delay(query)

        if delay is not None:
            self._notify_after(delay, KIKI_NAME, msg)
            unit = "second" if delay < 60 else "minute"
            amt  = delay if delay < 60 else delay // 60
            return f"i'll remind you in {amt} {unit}{'s' if amt != 1 else ''}."
        else:
            try:
                self._notify_now(KIKI_NAME, msg)
                return "notification sent."
            except RuntimeError as e:
                return str(e)

    # -----------------------------------------------------------------------
    # Parsing
    # -----------------------------------------------------------------------

    def _parse_delay(self, message: str) -> int | None:
        match = _TIME_PATTERN.search(message)
        if not match:
            return None
        amount = int(match.group(1))
        unit   = match.group(2).lower()
        if unit.startswith("s"): return amount
        if unit.startswith("m"): return amount * 60
        if unit.startswith("h"): return amount * 3600
        return None

    def _extract_message(self, query: str) -> str:
        msg = query.strip()
        for trigger in (
            "remind me to", "remind me about", "remind me",
            "notify me about", "notify me to", "notify me",
            "alert me about", "alert me to", "alert me",
            "set a reminder for", "set a reminder to", "set a reminder",
            "send a notification", "send me a popup",
            "give me a reminder",
        ):
            if msg.lower().startswith(trigger):
                msg = msg[len(trigger):].strip()
                break
        return _TIME_PATTERN.sub("", msg).strip(" ,.") or "reminder"

    # -----------------------------------------------------------------------
    # Notification dispatch
    # -----------------------------------------------------------------------

    def _notify_now(self, title: str, message: str) -> None:
        if sys.platform == "win32":
            self._notify_windows(title, message)
        else:
            self._notify_plyer(title, message)

    def _notify_windows(self, title: str, message: str) -> None:
        try:
            from plyer import notification
            notification.notify(
                title=title, message=message,
                app_name=KIKI_NAME, timeout=8,
            )
        except Exception:
            ps_script = (
                f"[Windows.UI.Notifications.ToastNotificationManager, "
                f"Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
                f"$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02;"
                f"$xml = [Windows.UI.Notifications.ToastNotificationManager]"
                f"::GetTemplateContent($template);"
                f"$xml.GetElementsByTagName('text')[0].AppendChild("
                f"$xml.CreateTextNode('{title}')) | Out-Null;"
                f"$xml.GetElementsByTagName('text')[1].AppendChild("
                f"$xml.CreateTextNode('{message}')) | Out-Null;"
                f"$toast = [Windows.UI.Notifications.ToastNotification]::new($xml);"
                f"[Windows.UI.Notifications.ToastNotificationManager]"
                f"::CreateToastNotifier('{KIKI_NAME}').Show($toast);"
            )
            subprocess.Popen(
                ["powershell", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def _notify_plyer(self, title: str, message: str) -> None:
        try:
            from plyer import notification
            notification.notify(
                title=title, message=message,
                app_name=KIKI_NAME, timeout=8,
            )
        except Exception as e:
            raise RuntimeError(f"notification failed: {e}")

    def _notify_after(self, delay_s: int, title: str, message: str) -> None:
        def _worker():
            time.sleep(delay_s)
            try:
                self._notify_now(title, message)
            except Exception as e:
                print(f"[notify] delayed notification failed: {e}")
        threading.Thread(target=_worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    skill = NotifySkill()

    assert skill._parse_delay("remind me in 5 minutes")  == 300
    assert skill._parse_delay("alert me in 2 hours")     == 7200
    assert skill._parse_delay("remind me in 30 seconds") == 30
    assert skill._parse_delay("remind me to drink water") is None

    assert skill._extract_message("remind me to drink water")          == "drink water"
    assert skill._extract_message("notify me about the meeting")       == "the meeting"
    assert skill._extract_message("remind me to stretch in 5 minutes") == "stretch"
    assert skill._extract_message("set a reminder for the call")       == "the call"

    print("notify.py — logic tests passed.")

    result = skill.run(query="remind me to drink water")
    assert result == "notification sent.", f"unexpected: {result}"
    print(f"immediate: {result}")

    result = skill.run(query="remind me to stretch in 2 seconds")
    assert "2 second" in result, f"unexpected: {result}"
    print(f"delayed:   {result}")

    time.sleep(3)
    print("notify.py — all tests passed.")