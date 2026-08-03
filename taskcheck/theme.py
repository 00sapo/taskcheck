import os
import re
import selectors
import termios
import tty

OSC11_QUERY = b"\x1b]11;?\x07"
OSC11_RESPONSE = re.compile(rb"\x1b]11;(?P<spec>[^\x07\x1b]+)(?:\x07|\x1b\\)")


def _parse_osc11_background(spec):
    text = spec.decode(errors="ignore").strip().lower()
    if text.startswith("rgb:"):
        channels = text[4:].split("/")[:3]
        try:
            rgb = [int(channel[: len(channel) // 2 or 1], 16) for channel in channels]
        except ValueError:
            return None
        return "light" if sum(rgb) / 3 >= 128 else "dark"
    return None


def _probe_osc11_background(timeout=0.2):
    try:
        with open("/dev/tty", "rb+", buffering=0) as tty_file:
            fd = tty_file.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                tty_file.write(OSC11_QUERY)
                sel = selectors.DefaultSelector()
                sel.register(tty_file, selectors.EVENT_READ)
                events = sel.select(timeout)
                if not events:
                    return None
                data = tty_file.read(128)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except (OSError, termios.error):
        return None
    if not data:
        return None
    match = OSC11_RESPONSE.search(data)
    if not match:
        return None
    return _parse_osc11_background(match.group("spec"))


def detect_theme(environ=None, config=None):
    environ = os.environ if environ is None else environ
    config = config or {}
    for key in ("TASKCHECK_THEME", "PI_THEME"):
        value = environ.get(key, "").strip().lower()
        if value in {"light", "dark"}:
            return value
    value = str(config.get("theme", "")).strip().lower()
    if value in {"light", "dark"}:
        return value
    osc11 = _probe_osc11_background()
    if osc11:
        return osc11
    value = environ.get("COLORFGBG", "")
    try:
        background = int(value.split(";")[-1])
    except ValueError:
        return "dark"
    return "light" if background >= 8 else "dark"
