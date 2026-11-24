# G710 Switch Mode Enabler

A small Windows tool that **attempts** to put the **Redragon Rift G710** controller into its **Nintendo Switch Pro Controller mode**, so emulators with native Pro Controller support can use its buttons, sticks and 6-axis motion sensors (gyro).

The controller's manual doesn't document this mode. This project exists because the mode turns out to be reachable, and nobody had written down how.

> **Status:** community-discovered behavior, tested on one controller. It is not documented by the manufacturer and may not work the same on every hardware revision or Windows setup. See [Troubleshooting](#troubleshooting).

---

## Contents

- [How it works](#how-it-works)
- [Which method should I use?](#which-method-should-i-use)
- [Method 1: HTML page (recommended)](#method-1-html-page-recommended)
- [Method 2: Portable executable](#method-2-portable-executable)
- [Method 3: Run the Python script](#method-3-run-the-python-script)
- [Method 4: Device Manager (fallback)](#method-4-device-manager-fallback)
- [Checking that it worked](#checking-that-it-worked)
- [Going back to normal](#going-back-to-normal)
- [Troubleshooting](#troubleshooting)
- [Building the executable yourself](#building-the-executable-yourself)
- [License and credit](#license-and-credit)
- [Disclaimer](#disclaimer)

---

## How it works

On Windows the G710 normally shows up in one of two modes. Holding the Home button switches between them:

| Mode | USB ID (`VID:PID`) | Notes |
|---|---|---|
| DInput / PS3-style | `2563:0575` | Default when plugged in |
| XInput | `045E:028E` | After a long press of Home |
| **Nintendo Switch Pro** | **`057E:2009`** | The hidden one, no button combo found |

Holding Home, holding a face button while connecting, and similar combos did **not** reach the Switch mode. Plugging the controller into a Linux machine did, and so did, by accident, having a browser page open that uses the Gamepad API.

What was observed, and what we conclude from it:

- With a web page open that continuously calls `navigator.getGamepads()`, plugging the controller in made it appear as `057E:2009`, which is the Pro Controller's USB ID. Emulators then even received gyro data.
- Having **Device Manager** open while plugging the controller in had the same effect.
- Having the Windows **Game Controllers** window (`joy.cpl`) open *prevented* it.

The mode change is not always stable. When watching the Game Controllers window while plugging in, a controller can appear, disappear immediately, and appear again, with the second one staying. The first is presumably the Pro Controller and the second the normal PS3 (DInput) mode. So the tool only counts the Switch Pro ID once it has stayed visible for a couple of seconds, instead of reacting to a brief flicker.

From this, the working theory is that the controller's firmware picks its mode depending on how the host computer behaves in the first moments after it is plugged in. Browsers and Device Manager enumerate and poll gamepad and HID devices as soon as they appear; the Game Controllers window grabs the device through the older DirectInput API, which keeps it in its default mode. This is a theory based on observation. It is not confirmed by the manufacturer.

**What this tool does:** it only imitates that early activity. While you plug the controller in, it polls the four XInput slots and repeatedly enumerates raw HID devices, then watches for a device with the ID `057E:2009` to appear. Seeing that ID is a good sign, not proof, so always [check it yourself](#checking-that-it-worked). It sends **no commands, no firmware writes, and no Pro Controller handshake** to the controller. It needs no drivers, no admin rights, and installs nothing.

Only to initialize the controller in the Pro Controller mode and you close it after that. Everything else (button mapping, gyro, rumble) is handled by your emulator or app, as it would be for a real Pro Controller.

---

## Which method should I use?

| # | Method | Needs | Reliability |
|---|---|---|---|
| 1 | HTML page | Chrome or Edge | Recommended, start here |
| 2 | Portable executable | Nothing | Alternative, shows a log of what happened |
| 3 | Python script | Python 3.8+ | Same as 2 |
| 4 | Device Manager | Nothing | Fallback, finicky |

All four rely on the same idea: something must be actively watching for gamepads **at the moment you plug the controller in**.

**General rules for every method:**

- Use the controller's normal connection, the same way you usually connect it.
- Close the Windows **Game Controllers / "Set up USB game controllers"** window (`joy.cpl`) first.
- Close Steam and other gamepad tools (BetterJoy, DS4Windows, etc.) so they don't grab the controller.
- Start the method **before** plugging the controller in, not after.

---

## Method 1: HTML page (recommended)

`switch_mode.html` is the original discovery. It does nothing except continuously call the browser's Gamepad API, which is what ends up making the controller stay in the Switch Pro Controller mode.

**Steps**

1. Close the Game Controllers window (`joy.cpl`) and any other gamepad software.
2. **Unplug the controller.**
3. Open `switch_mode.html` in **Chrome or Edge** (double-click it, or drag it into the browser). Other browsers are untested.
4. Keep that tab **visible and in front**.
5. **Plug the controller in.**
6. The page may show `The browser detected a gamepad: ...`. That does not confirm anything, so **check in your emulator** whether it became a Pro Controller ([how to verify](#checking-that-it-worked)).

**If it doesn't work the first time:**

1. Plug the controller in normally once, so it settles as a regular controller.
2. Unplug it.
3. **Refresh** the page (F5).
4. Plug the controller in again.

**Do**

- Keep the page in its own window or the front tab while plugging in.
- Refresh the page before each new attempt.

**Don't**

- Don't leave the page in a background tab. Browsers throttle hidden tabs and stop delivering gamepad data.
- Don't have the Game Controllers window open at the same time. It stops this from working.
- Don't plug the controller in before opening the page.

The page shows its message even for a controller in normal mode, so seeing it doesn't prove the switch happened. Verify in an emulator or in Device Manager.

---

## Method 2: Portable executable

A single `switch_mode.exe`. No installation, no Python, no dependencies.

**Steps**

1. Go to the [Releases](../../releases) page and download `switch_mode.exe`. (You can also get it from the latest successful run under the **Actions** tab, in the *Artifacts* section.)
2. Put it anywhere, for example your Desktop.
3. Close the Game Controllers window (`joy.cpl`), Steam, and any other gamepad software.
4. **Unplug the controller.**
5. Double-click `switch_mode.exe`. A console window opens and says it's probing.
6. **Now plug the controller in.**
7. Wait a few seconds. Check the log to see what happened. If Windows lists the Switch Pro ID and it **stays** for a couple of seconds, the log tells you the attempt finished and asks you to verify. If the ID only flickers and the controller settles in DInput (PS3) mode, the log tells you what to do next (see [Troubleshooting](#troubleshooting)).
8. Press Enter to close the window, then **check whether it really became a Pro Controller** in your emulator ([how to verify](#checking-that-it-worked)).

**Do**

- Run it before plugging the controller in.
- Leave the window open until it prints a result and then verify it yourself (it gives up after 60 seconds).
- If the mode drops back after you close the program, run it from a terminal with `switch_mode.exe --hold` and leave it open while you play.

**Don't**

- Don't plug the controller in first and run the program afterwards.
- Don't open the Game Controllers window while it's running.
- Don't hold Home or any other button while connecting. It isn't needed.

**Windows warnings:** the file is unsigned, so SmartScreen may show "Windows protected your PC" (click **More info**, then **Run anyway**), and some antivirus programs flag any unsigned PyInstaller-built program. If you're unsure, read the ~150-line source in `switch_mode.py` or [build the exe yourself](#building-the-executable-yourself).

**Options** (from a terminal): `--timeout N`, `--settle N` (seconds the ID must stay visible, default 2), `--hold`, `--pnp`, `--no-color`, `--verbose`, `--help`.

---

## Method 3: Run the Python script

Same logic as Method 2, without the executable.

**Steps**

1. Install [Python](https://www.python.org/downloads/) 3.8 or newer. In the installer, tick **Add python.exe to PATH**. No extra packages are needed.
2. Download `switch_mode.py` from this repository.
3. Close the Game Controllers window (`joy.cpl`), Steam, and other gamepad software.
4. **Unplug the controller.**
5. Open a terminal (Command Prompt or PowerShell) in the folder containing the script and run:
   ```
   python switch_mode.py
   ```
6. When it says it's probing, **plug the controller in**.
7. Wait for the log to say the attempt finished, then **check in your emulator** whether it really became a Pro Controller ([how to verify](#checking-that-it-worked)).

**Do**

- Run the script before plugging the controller in.
- Use `python switch_mode.py --hold` if the mode drops back once the script exits.
- Try `--pnp` if the default doesn't work. It adds a Device-Manager-style device scan.

**Don't**

- Don't run it on Linux or macOS. It uses Windows APIs and exits immediately there. (Linux already detects the controller as a Pro Controller.)
- Don't plug the controller in before starting the script.
- Don't leave the Game Controllers window open.

---

## Method 4: Device Manager (fallback)

Simply having Device Manager open when you plug in has been enough to trigger the switch. No tools are needed.

**Steps**

1. Close the Game Controllers window (`joy.cpl`) and any other gamepad software.
2. **Unplug the controller.**
3. Press **Win + X** and choose **Device Manager** (or press Win + R, type `devmgmt.msc`, press Enter).
4. Leave the Device Manager window open and visible.
5. **Plug the controller in.**
6. In Device Manager, expand **Human Interface Devices** and check the controller's hardware ID ([how](#checking-that-it-worked)), or just test it in your emulator.

**Do**

- Keep Device Manager open the entire time you plug in.
- Repeat the unplug and plug-in if it came up in normal mode the first time.

**Don't**

- Don't open the Game Controllers window (`joy.cpl`) at the same time.
- Don't open Device Manager after plugging the controller in.
- Don't expect this to be as reliable as the other methods.

---

## Checking that it worked

**In Game Controllers window (`joy.cpl`):** if it looks like this, don't panic! This means **it's in the Switch Pro mode**, but windows don't know how to read this kind of controller, but any app that supports it, can use it.
<img width="604" height="364" alt="" src="https://github.com/user-attachments/assets/69538a7f-3a65-4b15-bc77-a327e26fcbab" />


**In an emulator or app** that supports the Pro Controller: it should show up as a *Nintendo Pro Controller* (or similar), and motion data should be available. If it doesn't, the attempt didn't work.

**In Device Manager:**

1. Expand **Human Interface Devices**.
2. Right-click the controller, choose **Properties**, open the **Details** tab.
3. Set the property to **Hardware Ids**.
4. Look for `VID_057E&PID_2009`. That means Switch Pro mode. `VID_2563&PID_0575` or `VID_045E&PID_028E` mean it's still in a normal mode.

---

## Going back to normal

Based on our testing, unplugging the controller and plugging it in again **without** any of the methods above returns it to its normal DInput mode (Home long-press then toggles XInput). This isn't guaranteed for every setup. A full unplug and, if needed, a PC restart will reset things.

---

## Troubleshooting

- **The controller ends up in DInput (PS3) mode, or the tool says the ID only flickered:**
  1. Hold the **Home** button until the controller switches to **XInput** mode.
  2. **Unplug** the controller.
  3. **Close** the program and open it again.
  4. **Plug** the controller back in.
- **Times out or stays in normal mode:** unplug, make sure `joy.cpl`, Steam and other gamepad tools are closed, start the method, then plug in again. I also recommend connecting the controller normally, press the home button to put in in XInput mode, then unpluging it. then run the run the script/program/html then plug in the controller again. it should work this way. try at least 3 more times before attempting a different method. also  Try `--pnp` in case that works for you.
- **The page or program reports something, but it isn't acting as a Pro Controller:** those messages only show an attempt was made and a device ID was seen. Verify with the [hardware ID](#checking-that-it-worked).
- **Mode drops after closing the tool:** use `--hold` and keep it running while you play.
- **Works in the script but not the exe (or the other way round):** please open an issue and include which one worked.
- **Different hardware ID:** if your controller shows different IDs than those in the table above, open an issue with the IDs. It may be a different revision.

---

## Building the executable yourself

The repository includes a GitHub Actions workflow (`.github/workflows/build.yml`) that builds `switch_mode.exe` with PyInstaller on a Windows runner.

- **Every push to `main`** builds the exe and attaches it to the workflow run as an artifact.
- **Pushing a version tag** (for example `v1.0.0`) builds it and publishes it on the Releases page:
  ```
  git tag v1.0.0
  git push origin v1.0.0
  ```
- **Locally on Windows:**
  ```
  pip install pyinstaller
  pyinstaller --onefile --console --name switch_mode switch_mode.py
  ```
  The result is `dist/switch_mode.exe`.

---

## License and credit

Released under the [MIT License](LICENSE). You may use, modify and redistribute this project, including in forks and derivative works, provided you keep the copyright notice and license text, which credits the original author:

**Copyright (c) 2026 [valo-io](https://github.com/valo-io)**

If this helped you, a star or a link back is appreciated but not required.

---

## Disclaimer

This is an independent, unofficial community project. It is **not affiliated with, authorized, sponsored, or endorsed by** Nintendo, Redragon, Microsoft, Sony, Valve, Google, or any other company or product mentioned here. All product names, logos, brands and trademarks, including *Nintendo*, *Nintendo Switch*, *Switch Pro Controller*, *Redragon*, *Rift G710*, *Windows*, *Xbox*, *XInput*, *DirectInput*, *PlayStation*, *Steam*, *Chrome*, *Edge*, *GitHub*, and *Python*, are the property of their respective owners and are used only to identify the hardware and software this tool works with.

The tool does not modify controller firmware, send commands to the device, or circumvent any protection. It only observes devices and polls standard Windows input APIs. It is provided **as is, without warranty of any kind**; you use it at your own risk.
