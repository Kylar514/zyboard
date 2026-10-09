# zyboard

ZMK firmware configuration for a wireless split ergonomic keyboard built on the
[Cyboard](https://www.cyboard.digital/) flex-PCB system in a Dactyl Manuform
number-row body.

<img width="2048" height="1536" alt="268fbecc-fe1b-4f6f-9f98-cbf9358c3071" src="https://github.com/user-attachments/assets/c6ff3c1e-c0f6-4f66-9ba3-f55597b9b367" />


---

## Hardware

| Component                 | Part                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Body                      | Cyboard — Dactyl Manuform, number-row variant                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Controllers (both halves) | [nice!nano v2 nRF52840](https://www.amazon.com/AITRIP-Development-Bluetooth-Management-Module%EF%BC%8CNano/dp/B0DCZJKYL1/ref=sr_1_1?crid=2LOQ1C2L2H0LA&dib=eyJ2IjoiMSJ9.AAo6u5vX-cr0obYWEdxxF5J0l3yqb6BGdFZTik3Gbd8hcK8aaIWKEBItbMwowyBR_wV076nhmzThK1FUu02jxFFJ1rEQdkIDtbMuahvLWo5lbz3lX3RVYLAent-__ABG9nFbgU49tYmTN_gmfHOtMZ9zjomzj2xkcJ-o709yYIe48FrIBH1lkRc7IDFMRFkkT4W4lUY61_2xnPrz7XTDJ8AZ46EOCiwrfgS0qAgjtQkJmvNKY-gtxE5to4mDQsQNvPo1Hq1T06G3dcYkwdr5ZzMcgpg3sluF21oD1MZ1FlA.mUjyJdDF3oYGljemq8d2I0FxaF55hYOAR3-4icy_T8c&dib_tag=se&keywords=nice!Nano%2Bv2&qid=1791375846&s=electronics&sprefix=nice%2Bnano%2Bv2%2Celectronics%2C139&sr=1-1&th=1) |
| Dongle                    | [Seeed XIAO nRF52840](https://www.amazon.com/dp/B0DJ6NZVJT?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_1&th=1)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Batteries                 | 3000 mAh (both halves)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Switches                  | [Gateron Black Ink V2s](https://www.gateron.co/products/gateron-ink-switch)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Keycaps                   | [YMDK DSA Black Blank keycaps](https://www.amazon.com/dp/B07S18VCDN)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Firmware                  | ZMK on Zephyr RTOS                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

### Dongle connector note

The XIAO nRF52840 has a **female USB-C port**. To use it as a plug-in dongle you
need an adapter:

- **USB-A hosts** (desktop, laptop with USB-A port): female USB-C to male USB-A
  adapter (~$2)
- **USB-C hosts** (modern laptop): female USB-C to male USB-C coupler / gender
  changer

The dongle plugs into the adapter; the adapter plugs into the computer. No
firmware change is needed — this is purely a physical connector solution.

---

## How the split topology works

```
[Left half]  <-- BLE -->  [XIAO Dongle]  <-- USB --> [Computer]
[Right half] <-- BLE -->  (central)
 (peripheral)              (USB HID)
 (peripheral)
```

The dongle is the **USB central**. Both halves are **BLE peripherals** that
connect wirelessly to the dongle. The dongle runs the keymap logic and presents
as a standard USB HID keyboard to the host computer.

Without the dongle plugged in, the keyboard does not function — the halves
cannot connect directly to a host when configured this way.

**PC wake-from-sleep:** Pressing any key sends a USB remote wakeup signal
through the dongle, waking the computer. On Windows you must enable this once:
Device Manager → find the keyboard under Human Interface Devices → Properties →
Power Management → check "Allow this device to wake the computer". On Linux:
`echo enabled | sudo tee /sys/bus/usb/devices/<device>/power/wakeup`

---

## Power / sleep behavior

| State      | Trigger           | Effect                  | Keypress response                    |
| ---------- | ----------------- | ----------------------- | ------------------------------------ |
| Active     | —                 | RGB on, BLE connected   | Instant                              |
| Idle       | 1 min inactivity  | RGB off, BLE stays up   | Instant                              |
| Deep sleep | 60 min inactivity | MCU shuts down, BLE off | A few seconds to reconnect to dongle |

The deep-sleep timer runs from the last keypress. After 1 minute, RGB turns off
while the halves stay awake and BLE-connected, so typing resumes immediately.
After 60 minutes total inactivity, each half enters deep sleep; a keypress wakes
it and it reconnects to the dongle before keystrokes reach the host.
Reconnection time varies with radio conditions. Each half briefly shows a red
breathing battery alert using its own battery reading: 60 seconds at 10% or
lower, extended to 120 seconds if it reaches 5% or lower. It then restores that
half's previous RGB color, effect, and on/off state. The dongle has no battery
indicator.

---

## Repo structure

```
zyboard/
├── .github/
│   └── workflows/
│       └── build.yml          # CI: delegates to ZMK's reusable build workflow.
│                              # Reads build.yaml to determine what to compile.
│
├── boards/
│   └── shields/
│       └── imprint/           # Imprint shield definition (self-contained, no external deps).
│           ├── Kconfig.shield     # Declares SHIELD_IMPRINT_LEFT/RIGHT/DONGLE symbols.
│           ├── Kconfig.defconfig  # Feature defaults: keyboard name, split roles,
│           │                      # RGB settings, dongle BT connection counts.
│           ├── imprint.conf       # Shared shield Kconfig fragment (see Kconfig.defconfig).
│           ├── imprint_left.conf  # Left-half Kconfig overrides (currently none).
│           ├── imprint_right.conf # Right-half Kconfig overrides (currently none).
│           ├── imprint_dongle.conf# Dongle Kconfig overrides (currently none).
│           ├── imprint.dtsi       # Core shield DTS: all 14 matrix transforms +
│           │                      # kscan GPIO matrix definition.
│           ├── imprint_left.overlay   # Left-half row GPIO assignments.
│           ├── imprint_right.overlay  # Right-half row GPIO assignments + row-offsets.
│           ├── imprint_dongle.overlay # Mock kscan + active transform for the dongle.
│           └── boards/
│               └── nice_nano_nrf52840_zmk.overlay # SPI3 + WS2812 for nice!nano v2.
│
├── config/
│   ├── west.yml        # West manifest: pins ZMK main as the only dependency.
│   ├── zephyr/module.yml # Local west-workspace module path; board_root points to ..
│   ├── imprint.conf    # Active Kconfig: power/sleep/BT/RGB settings.
│   ├── imprint.keymap  # Active keymap: all layers and behaviors.
│   └── info.json       # Key position spec for GUI keymap editors.
│
├── zephyr/module.yml  # Registers this repository as a Zephyr module/board root.
│
└── build.yaml         # Build matrix: lists all board+shield targets for CI.
```

### What `zephyr/module.yml` does

The root `zephyr/module.yml` lets the ZMK reusable build workflow discover the
local shield definitions. For a west workspace initialized inside this
repository, the manifest project path is `config`, so `config/zephyr/module.yml`
points the board root back to the repository root. Local builds pass `config/`
as `ZMK_EXTRA_MODULES`.

---

## Layers

The active keymap (`config/imprint.keymap`) uses the
`dactyl_manuform_number_row` matrix transform and defines 5 layers:

use [Keymap editor](https://nickcoutsos.github.io/keymap-editor/) to view and edit

### Layer 0 — Default (QWERTY)

```
= 1 2 3 4 5  |  6 7 8 9 0 -
Tab Q W E R T|  Y U I O P \
Ctrl A S D F G|  H J K L ; '/`
Shft Z X C V B|  N M , . / Shft
↑ ↓ Esc Rep  |      [ ] ← →

         Ret Del Alt  |  →4  Bsp  Spc
         GUI tog2 tog1|   0   3   GUI
```

- `Shft` (both sides): tap = Shift, double-tap = Caps Word
- `'/`` `: tap = `'`, double-tap = `` ` `` (tap-dance)
- `Rep`: key repeat (repeats the last key sent)
- `→4`: switch to layer 4 (game)
- `tog1` / `tog2`: toggle layer 1 / 2
- `0` / `3`: switch to layer 0 / 3

### Layer 1 — F-keys

F1–F12 mapped to the right half in a 3×4 grid (F10/F11/F12 on top row, F1/F2/F3
on bottom). All other keys transparent.

### Layer 2 — Number pad + BT + RGB

Left half: BT profile select (BT_SEL 0–4) and BT_CLR on bottom-left. Right half:
numpad (7/8/9, 4/5/6, 1/2/3, 0) + full RGB underglow controls (toggle, hue,
saturation, brightness, speed, effect cycling).

### Layer 3 — Media

- Previous track, next track, volume down, volume up, mute, play/pause
- Mapped to the right half home and upper rows.

### Layer 4 — Game

WASD locked to their physical positions regardless of any layer remapping. All
other keys transparent. Switch back to layer 0 with the `→0` key in the thumb
cluster.

---

## Building

### GitHub Actions (automatic)

Push to any branch or open a pull request — the workflow in
`.github/workflows/build.yml` runs automatically and produces `.uf2` artifacts
for all targets in `build.yaml`:

| Artifact                            | Board                           | Purpose                   |
| ----------------------------------- | ------------------------------- | ------------------------- |
| `imprint_left`                      | nice!nano v2 (`nice_nano//zmk`) | Left half firmware        |
| `imprint_right`                     | nice!nano v2 (`nice_nano//zmk`) | Right half firmware       |
| `imprint_dongle`                    | XIAO nRF52840                   | Dongle firmware           |
| `settings_reset` (`nice_nano//zmk`) | nice!nano v2                    | Clear settings on a half  |
| `settings_reset` (`xiao_ble//zmk`)  | XIAO nRF52840                   | Clear dongle settings     |

### Which firmware to flash

Routine updates use the normal `.uf2` files; they preserve saved settings and
pairing, so **do not flash `settings_reset` for ordinary changes**.

| Change | Normal firmware to flash |
| --- | --- |
| Layers or key bindings in `config/imprint.keymap` | Dongle; it is the split central and processes the keymap |
| Power, sleep, RGB, or battery-indicator settings | Both nice!nano halves |
| Dongle-specific USB/Bluetooth settings | Dongle |
| Unsure which build targets are affected | Normal firmware to all three devices |

### Viewing battery levels on Linux

The dongle firmware exposes a second, vendor-defined USB HID interface for the
two split battery readings. After building and flashing the normal dongle UF2,
install the udev rule from this repository so your desktop user can read it:

```sh
sudo install -Dm644 udev/70-zyboard-battery.rules /etc/udev/rules.d/70-zyboard-battery.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw
```

Unplug and reconnect the dongle, then run the dependency-free Python monitor:

```sh
python3 tools/battery_monitor.py
```

If it cannot find the interface automatically, list `/dev/hidraw*` and pass the
battery interface explicitly with `--device /dev/hidrawN`. The two slots are
assigned in BLE pairing order, which may not correspond consistently to left
and right. A slot shows `unknown` until its first battery report arrives. Battery
percentages are estimates based on voltage.

Use `settings_reset` on **all three devices** when re-pairing is needed—for
example, after changing the split central role, replacing a controller, or
troubleshooting stale split bonds. It clears persistent settings, including RGB
state and Bluetooth profiles, not just split bonds. Flash the reset image to all
three first, then restore the normal left, right, and dongle firmware. The reset
image disables Bluetooth, so the keyboard will not work until normal firmware is
restored.

### Local build

Follow the [ZMK getting started guide](https://zmk.dev/docs/development/setup)
to set up a west workspace, then:

```sh
west build -s zmk/app -b nice_nano//zmk -- -DSHIELD=imprint_left -DZMK_CONFIG=/path/to/zyboard/config -DZMK_EXTRA_MODULES=/path/to/zyboard -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=n
west build -s zmk/app -b nice_nano//zmk -- -DSHIELD=imprint_right -DZMK_CONFIG=/path/to/zyboard/config -DZMK_EXTRA_MODULES=/path/to/zyboard
west build -s zmk/app -b xiao_ble//zmk -- -DSHIELD=imprint_dongle -DZMK_CONFIG=/path/to/zyboard/config -DZMK_EXTRA_MODULES=/path/to/zyboard
```

---

## First-time setup

Flash the normal left, right, and dongle firmware to their matching devices, then
power all three on. ZMK automatically pairs split devices that have no saved bond.
If they fail to pair because of stale bonds or a central-role change, follow the
`settings_reset` procedure above.

---

## Editing the keymap

Edit `config/imprint.keymap`. The file uses standard ZMK keymap syntax. Push
your changes and GitHub Actions will build new firmware automatically.

Key references:

- [ZMK keycodes](https://zmk.dev/docs/codes)
- [ZMK behaviors](https://zmk.dev/docs/behaviors/key-press)
- [ZMK layers](https://zmk.dev/docs/behaviors/layers)

To switch to a different matrix transform (different physical layout variant),
change the `chosen` node at the top of `config/imprint.keymap`:

```dts
chosen { zmk,matrix_transform = &dactyl_manuform_number_row; };
```

Available transforms are defined in `boards/shields/imprint/imprint.dtsi`.
