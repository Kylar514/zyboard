# zyboard

ZMK firmware configuration for a wireless split ergonomic keyboard built on the
[Cyboard Imprint](https://www.cyboard.digital/) flex-PCB system in a Dactyl Manuform
number-row body.

---

## Hardware

| Component | Part |
|-----------|------|
| Body | Cyboard Imprint — Dactyl Manuform, number-row variant |
| Controllers (both halves) | nice!nano v2 (nRF52840) |
| Dongle | Seeed XIAO nRF52840 |
| Batteries | 3000 mAh (both halves) |
| RGB underglow | WS2812 strip, 50 LEDs per half |
| Firmware | ZMK on Zephyr RTOS |

### Dongle connector note

The XIAO nRF52840 has a **female USB-C port**. To use it as a plug-in dongle you
need an adapter:

- **USB-A hosts** (desktop, laptop with USB-A port): female USB-C to male USB-A adapter (~$2)
- **USB-C hosts** (modern laptop): female USB-C to male USB-C coupler / gender changer

The dongle plugs into the adapter; the adapter plugs into the computer. No firmware
change is needed — this is purely a physical connector solution.

---

## How the split topology works

```
[Left half]  <-- BLE -->  [XIAO Dongle]  <-- USB --> [Computer]
[Right half] <-- BLE -->  (central)
 (peripheral)              (USB HID)
 (peripheral)
```

The dongle is the **USB central**. Both halves are **BLE peripherals** that connect
wirelessly to the dongle. The dongle runs the keymap logic and presents as a standard
USB HID keyboard to the host computer.

Without the dongle plugged in, the keyboard does not function — the halves cannot
connect directly to a host when configured this way.

**PC wake-from-sleep:** Pressing any key sends a USB remote wakeup signal through the
dongle, waking the computer. On Windows you must enable this once: Device Manager →
find the keyboard under Human Interface Devices → Properties → Power Management →
check "Allow this device to wake the computer". On Linux:
`echo enabled | sudo tee /sys/bus/usb/devices/<device>/power/wakeup`

---

## Power / sleep behavior

| State | Trigger | Effect | Keypress response |
|-------|---------|--------|-------------------|
| Active | — | RGB on, BLE connected | Instant |
| Idle | 1 min inactivity | RGB off, BLE stays up | Instant |
| Deep sleep | 15 min inactivity | MCU shuts down, BLE off | ~1–3s reconnect to dongle |

The 15-minute deep sleep timer runs from the last keypress. The idle timer (RGB off)
triggers first at 1 minute. Once in deep sleep, any keypress wakes the MCU; it then
re-advertises and reconnects to the dongle over BLE before keystrokes reach the host.
The ~1–3s reconnect delay is inherent to BLE and cannot be reduced further in firmware.

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

The root `zephyr/module.yml` lets the ZMK reusable build workflow discover the local
shield definitions. For a west workspace initialized inside this repository, the
manifest project path is `config`, so `config/zephyr/module.yml` points the board root
back to the repository root. Local builds pass `config/` as `ZMK_EXTRA_MODULES`.

---

## Layers

The active keymap (`config/imprint.keymap`) uses the `dactyl_manuform_number_row`
matrix transform and defines 5 layers:

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

F1–F12 mapped to the right half in a 3×4 grid (F10/F11/F12 on top row,
F1/F2/F3 on bottom). All other keys transparent.

### Layer 2 — Number pad + BT + RGB

Left half: BT profile select (BT_SEL 0–4) and BT_CLR on bottom-left.
Right half: numpad (7/8/9, 4/5/6, 1/2/3, 0) + full RGB underglow controls
(toggle, hue, saturation, brightness, speed, effect cycling).

### Layer 3 — Media

- Previous track, next track, volume down, volume up, mute, play/pause
- Mapped to the right half home and upper rows.

### Layer 4 — Game

WASD locked to their physical positions regardless of any layer remapping.
All other keys transparent. Switch back to layer 0 with the `→0` key in the
thumb cluster.

---

## Building

### GitHub Actions (automatic)

Push to any branch or open a pull request — the workflow in
`.github/workflows/build.yml` runs automatically and produces `.uf2` artifacts for
all targets in `build.yaml`:

| Artifact | Board | Purpose |
|----------|-------|---------|
| `imprint_left` | nice!nano v2 (`nice_nano//zmk`) | Left half firmware |
| `imprint_right` | nice!nano v2 (`nice_nano//zmk`) | Right half firmware |
| `imprint_dongle` | XIAO nRF52840 | Dongle firmware |
| `settings_reset` (`nice_nano//zmk`) | nice!nano v2 | Bond wipe for both halves |
| `settings_reset` (`xiao_ble//zmk`) | XIAO nRF52840 | Bond wipe for dongle |

### Local build

Follow the [ZMK getting started guide](https://zmk.dev/docs/development/setup) to set
up a west workspace, then:

```sh
west build -s zmk/app -b nice_nano//zmk -- -DSHIELD=imprint_left -DZMK_CONFIG=/path/to/zyboard/config -DZMK_EXTRA_MODULES=/path/to/zyboard -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=n
west build -s zmk/app -b nice_nano//zmk -- -DSHIELD=imprint_right -DZMK_CONFIG=/path/to/zyboard/config -DZMK_EXTRA_MODULES=/path/to/zyboard
west build -s zmk/app -b xiao_ble//zmk -- -DSHIELD=imprint_dongle -DZMK_CONFIG=/path/to/zyboard/config -DZMK_EXTRA_MODULES=/path/to/zyboard
```

---

## First-time setup / re-pairing

> **This step is mandatory.** Skipping it is the most common cause of pairing failures
> with a dongle setup.

1. **Flash `settings_reset`** to all three devices:
   - Both halves: use the `nice_nano//zmk` settings_reset binary
   - Dongle: use the `xiao_ble//zmk` settings_reset binary
   - To enter bootloader: double-press the reset button; a USB drive named `NRF52BOOT`
     or `XIAO-SENSE` appears; drag-and-drop the `.uf2` file onto it
2. **Flash actual firmware** to each device (left, right, dongle)
3. **Power on all three** — they advertise and pair automatically on first boot

Repeat this full sequence any time you need to re-pair (e.g. after flashing new
firmware that changes the split configuration).

---

## Editing the keymap

Edit `config/imprint.keymap`. The file uses standard ZMK keymap syntax. Push your
changes and GitHub Actions will build new firmware automatically.

Key references:
- [ZMK keycodes](https://zmk.dev/docs/codes)
- [ZMK behaviors](https://zmk.dev/docs/behaviors/key-press)
- [ZMK layers](https://zmk.dev/docs/behaviors/layers)

To switch to a different matrix transform (different physical layout variant), change
the `chosen` node at the top of `config/imprint.keymap`:

```dts
chosen { zmk,matrix_transform = &dactyl_manuform_number_row; };
```

Available transforms are defined in `boards/shields/imprint/imprint.dtsi`.
