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
    --hold        keep probing after success until Ctrl+C
    --pnp         also run a Device-Manager-style pnputil enumeration (off by default)
    --verbose     print every probe round

Read https://github.com/valo-io/g710-switch-pro-mode#troubleshooting if it didn't work.

Copyright (c) 2026 valo-io - MIT License. Not affiliated with any trademark owner.
"""
import argparse
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes

if sys.platform != "win32":
    sys.exit("This tool is for Windows only.")

TARGET = "VID_057E&PID_2009"
KNOWN = {
    "VID_2563&PID_0575": "DInput / PS3 mode",
    "VID_045E&PID_028E": "XInput mode",
    TARGET: "device with the Switch Pro ID (057E:2009)",
}

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


def modes(names):
    return [label for key, label in KNOWN.items() if any(key in n for n in names)]


def main():
    ap = argparse.ArgumentParser(description="Attempt to put a Redragon G710 into Nintendo Switch Pro mode.")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--hold", action="store_true")
    ap.add_argument("--pnp", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    names = hid_names()
    if any(TARGET in n for n in names):
        print("Windows already lists a device with the Switch Pro ID (057E:2009).")
        print("Please check in an emulator or app that it really behaves as a Pro Controller.")
        if not args.hold:
            return 0
    elif modes(names):
        print("Currently detected:", ", ".join(modes(names)))
        print("Unplug the controller first, then plug it in once I'm probing.")

    print("Probing... plug the controller in now. (Ctrl+C to abort)")
    t0 = time.time()
    last_pnp = 0.0
    last_state = None
    ok = False
    timeout = args.timeout
    try:
        while time.time() - t0 < timeout:
            poll_xinput()
            names = hid_names()
            state = tuple(modes(names))
            if state != last_state:
                print(f"[{time.time() - t0:5.1f}s] detected:", ", ".join(state) or "no known controller")
                last_state = state
            if not ok and any(TARGET in n for n in names):
                ok = True
                print("ATTEMPT FINISHED: Windows now lists a device with the Switch Pro ID (057E:2009).")
                print("This does not prove it works. Please check in an emulator or app that the")
                print("controller really behaves as a Pro Controller (buttons, sticks, gyro).")
                print("")
                print("Read https://github.com/valo-io/g710-switch-pro-mode#troubleshooting if it didn't work.")
                if not args.hold:
                    return 0
                print("Holding; press Ctrl+C to exit.")
                timeout = float("inf")
            if args.pnp and time.time() - last_pnp > 1.0:
                pnp_probe()
                last_pnp = time.time()
            if args.verbose:
                print("  round", round(time.time() - t0, 2))
            time.sleep(0.005)
    except KeyboardInterrupt:
        print("Stopped.")
        return 0 if ok else 1

    if not ok:
        print("Attempt timed out: no device with the Switch Pro ID (057E:2009) appeared.")
        print("Close joy.cpl and other gamepad apps, unplug, and try again.")
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
