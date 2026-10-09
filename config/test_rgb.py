"""Check the generated RGB source against the fetched ZMK implementation.

Run: python3 config/test_rgb.py [path/to/zmk/app/src/rgb_underglow.c]
These are source regression checks; on-device idle/deep-sleep tests are still needed.
"""

from pathlib import Path
import re
import sys

from fix_rgb import patch


def function(source, name):
    match = re.search(r"\b" + name + r"\([^;{}]*\)\s*\{", source)
    assert match is not None, name
    start = match.end() - 1
    depth = 1
    end = start + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "zmk/app/src/rgb_underglow.c"
source = source_path.read_text()
fixed = patch(source)

# Temporary idle and alerts must never mutate/persist user preferences.
idle = function(fixed, "rgb_underglow_auto_state")
assert "rgb_awake = target_wake_state" in idle
assert "state.on" not in idle and "save_state" not in idle
alert = function(fixed, "imprint_rgb_battery_alert")
assert "alert_state =" in alert and "alert_until =" in alert
assert "state.on =" not in alert and "save_state" not in alert
tick = function(fixed, "zmk_rgb_underglow_tick")
assert "render_state = alert ? &alert_state : &state" in tick
assert "!rgb_awake || (!state.on && !alert)" in tick
assert "pixels[i].r * 5" in tick
assert "ext_power_get(ext_power) != powered" in tick

# Hotkeys continue to save normal on/off/color preferences; dongle has no timer.
assert "state.on = true" in function(fixed, "zmk_rgb_underglow_on")
assert "state.on = false" in function(fixed, "zmk_rgb_underglow_off")
assert "save_state" in function(fixed, "zmk_rgb_underglow_set_hsb")
assert "!IS_ENABLED(CONFIG_SHIELD_IMPRINT_DONGLE)" in function(fixed, "refresh_rgb")
assert "if (!led_strip)" not in fixed

# Refuse to silently patch an incompatible upstream version.
try:
    patch(source.replace("static struct rgb_underglow_state state;", "/* upstream changed */"))
except ValueError:
    pass
else:
    raise AssertionError("incompatible source was accepted")

print("RGB source regression checks passed")
