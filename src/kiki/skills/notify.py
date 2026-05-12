"""
Skill: notify
Send a system notification. Cross-platform via plyer.
"""
from __future__ import annotations
import sys
import re

from ..config import KIKI_NAME

NAME        = "notify"
DESCRIPTION = "notify remind alert notification message popup"
EXAMPLES    = [
    "remind me to drink water",
    "send a notification",
    "notify me about the meeting",
    "set a reminder",
    "alert me in 5 minutes",
    "remind me to take a break",
    "send me a popup",
    "give me a reminder",
]
PARAMETERS      = {"query": "full user message"}
REQUIRES_VISION = False

# ---------------------------------------------------------------------------
# Timer parsing
# ---------------------------------------------------------------------------

_TIME_PATTERN = re.compile(
    r"in\s+(\d+)\s*(second|seconds|sec|minute|minutes|min|hour|hours|hr)s?",
    re.IGNORECASE,
)


def _parse_delay(message: str) -> int | None:
    """Return delay in seconds, or None if no time found."""
    match = _TIME_PATTERN.search(message)
    if not match:
        return None
    amount = int(match.group(1))
    unit   = match.group(2).lower()
    if unit.startswith("s"):
        return amount
    if unit.startswith("m"):
        return amount * 60
    if unit.startswith("h"):
        return amount * 3600
    return None


def _extract_message(query: str) -> str:
    """Strip trigger phrases to get the notification message."""
    msg = query.strip()
    for trigger in (
        "remind me to", "remind me about", "remind me",
        "notify me about", "notify me to", "notify me",
        "alert me about", "alert me to", "alert me",
        "set a reminder for", "set a reminder to", "set a reminder",
        "send a notification", "send me a popup",
        "give me a reminder",
    ):
        lower = msg.lower()
        if lower.startswith(trigger):
            msg = msg[len(trigger):].strip()
            break

    # strip time clause
    msg = _TIME_PATTERN.sub("", msg).strip(" ,.")
    return msg if msg else "reminder"


# ---------------------------------------------------------------------------
# Platform notification
# ---------------------------------------------------------------------------

def _notify_now(title: str, message: str) -> None:
    """Send an immediate system notification."""
    if sys.platform == "win32":
        _notify_windows(title, message)
    else:
        _notify_plyer(title, message)


def _notify_windows(title: str, message: str) -> None:
    try:
        from plyer import notification
        notification.notify(
            title       = title,
            message     = message,
            app_name    = KIKI_NAME,
            timeout     = 8,
        )
    except Exception:
        # fallback: Windows toast via PowerShell
        import subprocess
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


def _notify_plyer(title: str, message: str) -> None:
    try:
        from plyer import notification
        notification.notify(
            title    = title,
            message  = message,
            app_name = KIKI_NAME,
            timeout  = 8,
        )
    except Exception as e:
        raise RuntimeError(f"notification failed: {e}")


# ---------------------------------------------------------------------------
# Delayed notification
# ---------------------------------------------------------------------------

def _notify_after(delay_s: int, title: str, message: str) -> None:
    """Fire notification after delay_s seconds in a daemon thread."""
    import threading
    import time

    def _worker():
        time.sleep(delay_s)
        try:
            _notify_now(title, message)
        except Exception as e:
            print(f"[notify] delayed notification failed: {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(query: str = "", **kwargs) -> str:
    msg   = _extract_message(query)
    delay = _parse_delay(query)

    if delay is not None:
        _notify_after(delay, KIKI_NAME, msg)
        unit = "second" if delay < 60 else "minute"
        amt  = delay if delay < 60 else delay // 60
        return f"i'll remind you in {amt} {unit}{'s' if amt != 1 else ''}."
    else:
        try:
            _notify_now(KIKI_NAME, msg)
            return "notification sent."
        except RuntimeError as e:
            return str(e)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # parse delay
    assert _parse_delay("remind me in 5 minutes") == 300
    assert _parse_delay("alert me in 2 hours")    == 7200
    assert _parse_delay("remind me in 30 seconds") == 30
    assert _parse_delay("remind me to drink water") is None

    # extract message
    assert _extract_message("remind me to drink water")          == "drink water"
    assert _extract_message("notify me about the meeting")       == "the meeting"
    assert _extract_message("remind me to stretch in 5 minutes") == "stretch"
    assert _extract_message("set a reminder for the call")       == "the call"

    print("notify.py — logic tests passed.")
    print("sending a live notification...")

    result = run(query="remind me to drink water")
    assert result == "notification sent.", f"unexpected: {result}"
    print(f"immediate: {result}")

    result = run(query="remind me to stretch in 2 seconds")
    assert "2 second" in result, f"unexpected: {result}"
    print(f"delayed:   {result}")

    import time
    time.sleep(3)   # wait for delayed notification to fire
    print("notify.py — all tests passed.")