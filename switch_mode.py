"""
G710 Switch Mode Enabler (Windows, Python 3.8+, standard library only).

Attempts to put a Redragon Rift G710 controller into its Nintendo Switch Pro
Controller mode (USB ID 057E:2009) by imitating what a browser's gamepad code
does while the controller is being plugged in. It sends no commands to the
controller, and it cannot confirm the result: always verify in an emulator.

Usage:
    1. Close "Set up USB game controllers" (joy.cpl), Steam and other gamepad apps.
    2. Unplug the controller.
    3. Run:  python switch_mode.py
    4. Plug the controller in when asked.

Options:
    --timeout N   give up after N seconds (default 60)
    --settle N    the Switch Pro ID must stay visible for N seconds before it is
                  reported (default 2). The controller sometimes shows that ID for
                  a split second and then falls back to PS3 / DInput mode.
    --hold        keep probing after success until Ctrl+C
    --pnp         also run a Device-Manager-style pnputil enumeration (off by default)
    --no-color    plain text output
    --verbose     print every probe round

Read https://github.com/valo-io/g710-switch-pro-mode#troubleshooting if it didn't work.

Copyright (c) 2026 valo-io - MIT License. Not affiliated with any trademark owner.
"""
import argparse
import ctypes
import os
import re
import subprocess
import sys
import textwrap
import time
from ctypes import wintypes

if sys.platform != "win32":
    sys.exit("This tool is for Windows only.")

SWITCH = "VID_057E&PID_2009"
DINPUT = "VID_2563&PID_0575"
XINPUT = "VID_045E&PID_028E"

# key -> (label, color)
KNOWN = {
    DINPUT: ("DInput / PS3 mode", "yellow"),
    XINPUT: ("XInput mode", "magenta"),
    SWITCH: ("Switch Pro ID (057E:2009)", "green"),
}

# ---------------------------------------------------------------- console UI

_kernel32 = ctypes.windll.kernel32
_kernel32.GetStdHandle.restype = ctypes.c_void_p
_kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
_kernel32.GetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
_kernel32.SetConsoleMode.argtypes = [ctypes.c_void_p, wintypes.DWORD]

ANSI = {
    "reset": "\x1b[0m", "bold": "\x1b[1m", "dim": "\x1b[2m",
    "red": "\x1b[91m", "green": "\x1b[92m", "yellow": "\x1b[93m",
    "magenta": "\x1b[95m", "cyan": "\x1b[96m",
}
USE_COLOR = False


def setup_console(no_color):
    """Turn on ANSI colors (Windows 10+). Stays plain text if that isn't possible."""
    global USE_COLOR
    if no_color or os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return
    try:
        handle = _kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = wintypes.DWORD()
        if _kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            USE_COLOR = bool(_kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        USE_COLOR = False


def paint(text, *styles):
    if not USE_COLOR or not styles:
        return text
    return "".join(ANSI[x] for x in styles) + text + ANSI["reset"]


def say(tag, color, msg, t=None):
    stamp = paint(f"[{t:5.1f}s]", "dim") + " " if t is not None else ""
    print(f"{stamp}{paint(tag, 'bold', color)} {msg}")


COW = r"""
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||"""


def cowsay(text, color="yellow", width=46):
    """Print text in a speech bubble, held up by a cow."""
    lines = []
    for para in text.split("\n"):
        indent = "   " if re.match(r"\d\.", para) else ""
        lines.extend(textwrap.wrap(para, width, subsequent_indent=indent) or [""])
    w = max(len(line) for line in lines)
    box = [" " + "_" * (w + 2)]
    if len(lines) == 1:
        box.append("< " + lines[0].ljust(w) + " >")
    else:
        for i, line in enumerate(lines):
            if i == 0:
                left, right = "/", "\\"
            elif i == len(lines) - 1:
                left, right = "\\", "/"
            else:
                left, right = "|", "|"
            box.append(f"{left} {line.ljust(w)} {right}")
    box.append(" " + "-" * (w + 2))
    print()
    for row in box:
        print(paint(row, color))
    print(paint(COW.strip("\n"), "dim"))
    print()


def banner():
    line = "=" * 52
    print(paint(line, "magenta"))
    print(paint("  G710 Switch Mode Enabler", "bold", "magenta"))
    print(paint("  attempts to trigger Switch Pro Controller mode", "dim"))
    print(paint(line, "magenta"))
    print()


# ------------------------------------------------------------ device probing

user32 = ctypes.windll.user32
user32.GetRawInputDeviceList.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.GetRawInputDeviceList.restype = wintypes.UINT
user32.GetRawInputDeviceInfoW.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(wintypes.UINT)]
user32.GetRawInputDeviceInfoW.restype = wintypes.UINT

RIM_TYPEHID = 2
RIDI_DEVICENAME = 0x20000007
ERR = 0xFFFFFFFF


class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [("hDevice", ctypes.c_void_p), ("dwType", wintypes.DWORD)]


def hid_names():
    """Device paths of all HID devices Windows currently knows about."""
    count = wintypes.UINT(0)
    size = ctypes.sizeof(RAWINPUTDEVICELIST)
    if user32.GetRawInputDeviceList(None, ctypes.byref(count), size) == ERR or count.value == 0:
        return []
    arr = (RAWINPUTDEVICELIST * count.value)()
    n = user32.GetRawInputDeviceList(arr, ctypes.byref(count), size)
    if n == ERR:
        return []
    names = []
    for i in range(n):
        if arr[i].dwType != RIM_TYPEHID:
            continue
        sz = wintypes.UINT(0)
        user32.GetRawInputDeviceInfoW(arr[i].hDevice, RIDI_DEVICENAME, None, ctypes.byref(sz))
        buf = ctypes.create_unicode_buffer(sz.value + 1)
        user32.GetRawInputDeviceInfoW(arr[i].hDevice, RIDI_DEVICENAME, buf, ctypes.byref(sz))
        names.append(buf.value.upper())
    return names


try:
    _xinput = ctypes.windll.xinput1_4
except OSError:
    try:
        _xinput = ctypes.windll.xinput1_3
    except OSError:
        _xinput = None
_xbuf = ctypes.create_string_buffer(16)


def poll_xinput():
    if _xinput:
        for i in range(4):
            _xinput.XInputGetState(i, _xbuf)


def pnp_probe():
    """Enumerate PnP devices roughly the way Device Manager does."""
    try:
        subprocess.run(
            ["pnputil", "/enum-devices", "/connected", "/class", "HIDClass"],
            capture_output=True, timeout=10,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
    except Exception:
        pass


def current_modes(names):
    return frozenset(k for k in KNOWN if any(k in n for n in names))


def describe(keys):
    if not keys:
        return paint("no known controller", "dim")
    return "  ".join(paint(KNOWN[k][0], KNOWN[k][1]) for k in KNOWN if k in keys)


HELP_URL = "https://github.com/valo-io/g710-switch-pro-mode#troubleshooting"

VERIFY = ("Please open an emulator or app with Pro Controller support and check "
          "that it really behaves as a Pro Controller (buttons, sticks, gyro).")

DINPUT_HINT = (
    "The controller is in DInput (PS3) mode, not Switch Pro mode. Try this:\n"
    "1. Hold the Home button until the controller switches to XInput mode.\n"
    "2. Unplug the controller.\n"
    "3. Close this program and open it again.\n"
    "4. Plug the controller back in."
)


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Attempt to put a Redragon G710 into Nintendo Switch Pro mode.")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--settle", type=float, default=2.0)
    ap.add_argument("--hold", action="store_true")
    ap.add_argument("--pnp", action="store_true")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    setup_console(args.no_color)
    banner()

    keys = current_modes(hid_names())
    if SWITCH in keys:
        say("[INFO]", "cyan", "Windows already lists a device with the Switch Pro ID (057E:2009).")
        cowsay("Already there, but that is not proof. " + VERIFY, "green")
        if not args.hold:
            return 0
    elif DINPUT in keys:
        say("[INFO]", "cyan", "Currently detected: " + describe(keys))
        cowsay(DINPUT_HINT, "yellow")
        return 1
    elif keys:
        say("[INFO]", "cyan", "Currently detected: " + describe(keys))
        cowsay("A controller is already plugged in. Unplug it, then plug it back in while I'm probing.", "yellow")

    say("[....]", "cyan", "Probing. Plug the controller in now. (Ctrl+C to quit)")
    print()

    t0 = time.time()
    timeout = args.timeout
    last_keys = None
    last_pnp = 0.0
    armed = not keys           # True once the controller has been seen unplugged
    switch_since = None        # when the Switch Pro ID last appeared
    dinput_since = None        # when DInput mode last appeared
    ok = False
    hint_shown = False
    flickers = 0
    try:
        while time.time() - t0 < timeout:
            poll_xinput()
            now = time.time()
            t = now - t0
            keys = current_modes(hid_names())

            if keys != last_keys:
                say("[SEEN]", "cyan", describe(keys), t)
                last_keys = keys
            if not keys:
                armed = True

            # The Switch Pro ID only counts once it has stayed visible for --settle seconds.
            if SWITCH in keys:
                if switch_since is None:
                    switch_since = now
                if not ok and now - switch_since >= args.settle:
                    ok = True
                    say("[ OK ]", "green", f"The Switch Pro ID (057E:2009) stayed visible for {args.settle:g}s.", t)
                    cowsay("Attempt finished: Windows lists the Switch Pro ID and it stayed. "
                           "That is not proof, though! " + VERIFY, "green")
                    print(paint("Read " + HELP_URL + " if it didn't work.", "dim"))
                    if not args.hold:
                        return 0
                    say("[HOLD]", "cyan", "Holding. Press Ctrl+C to exit.")
                    timeout = float("inf")
            elif switch_since is not None:
                seen_for = now - switch_since
                switch_since = None
                if ok:
                    ok = False
                    say("[WARN]", "yellow", "The Switch Pro ID disappeared again. The controller fell back.", t)
                else:
                    flickers += 1
                    say("[WARN]", "yellow",
                        f"The Switch Pro ID showed up for only {seen_for:.1f}s, then vanished (a flicker).", t)

            # Settled in DInput without the Switch Pro ID: this attempt didn't work.
            if armed and not ok and SWITCH not in keys and DINPUT in keys:
                if dinput_since is None:
                    dinput_since = now
                if now - dinput_since >= args.settle and not hint_shown:
                    hint_shown = True
                    say("[FAIL]", "red", "The controller settled in DInput / PS3 mode.", t)
                    cowsay(DINPUT_HINT, "yellow")
                    print(paint("Read " + HELP_URL + " for more help.", "dim"))
                    if not args.hold:
                        return 1
            else:
                dinput_since = None

            if args.pnp and now - last_pnp > 1.0:
                pnp_probe()
                last_pnp = now
            if args.verbose:
                print(paint(f"  round {t:.2f}s", "dim"))
            time.sleep(0.005)
    except KeyboardInterrupt:
        print()
        say("[STOP]", "cyan", "Stopped.")
        return 0 if ok else 1

    if not ok:
        say("[FAIL]", "red", "Attempt timed out: the Switch Pro ID never stayed visible.")
        cowsay("Nothing stuck. Close joy.cpl and other gamepad apps, unplug the controller, "
               "and try again. If it keeps landing in PS3 (DInput) mode, hold Home to switch "
               "to XInput, unplug, restart this program, then plug in again.", "yellow")
        print(paint("Read " + HELP_URL + " for more help.", "dim"))
        return 1
    return 0


def _launched_by_double_click():
    """True when this process owns its console alone (e.g. started from Explorer)."""
    try:
        pids = (wintypes.DWORD * 8)()
        n = ctypes.windll.kernel32.GetConsoleProcessList(pids, 8)
        # A PyInstaller one-file exe runs as a bootloader process plus a child process.
        return n <= (2 if getattr(sys, "frozen", False) else 1)
    except Exception:
        return False


if __name__ == "__main__":
    code = main()
    if _launched_by_double_click():
        input("\nPress Enter to close...")
    sys.exit(code)
