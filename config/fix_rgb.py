"""Patch the fetched ZMK RGB implementation in the build tree, not the dependency.

Exact replacements fail closed if upstream changes the affected code.
"""

from pathlib import Path
import sys


def patch(source):
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError(f"Upstream RGB code changed near: {old[:80]!r}")
        source = source.replace(old, new, 1)

    replace("#if !DT_HAS_CHOSEN(zmk_underglow)",
            "#if !DT_HAS_CHOSEN(zmk_underglow) && !IS_ENABLED(CONFIG_SHIELD_IMPRINT_DONGLE)")
    replace("#define STRIP_CHOSEN DT_CHOSEN(zmk_underglow)\n#define STRIP_NUM_PIXELS DT_PROP(STRIP_CHOSEN, chain_length)",
            """#if IS_ENABLED(CONFIG_SHIELD_IMPRINT_DONGLE)
#define STRIP_NUM_PIXELS 1
#else
#define STRIP_CHOSEN DT_CHOSEN(zmk_underglow)
#define STRIP_NUM_PIXELS DT_PROP(STRIP_CHOSEN, chain_length)
#endif""")
    replace("static struct rgb_underglow_state state;", """static struct rgb_underglow_state state;
static bool rgb_awake = true;
static int64_t alert_until;
static struct rgb_underglow_state alert_state;
static struct rgb_underglow_state *render_state = &state;
static void refresh_rgb(void);

static bool rgb_alert_active(void) { return k_uptime_get() < alert_until; }

/* Alert rendering never changes or persists the user's RGB preferences. */
void imprint_rgb_battery_alert(uint32_t seconds) {
    alert_state = (struct rgb_underglow_state){
        .color = {.h = 0, .s = 100, .b = 5},
        .animation_speed = 1,
        .current_effect = UNDERGLOW_EFFECT_BREATHE,
        .animation_step = 1200,
        .on = true,
    };
    alert_until = k_uptime_get() + seconds * 1000;
    refresh_rgb();
}""")
    start = source.index("static void zmk_rgb_underglow_effect_solid")
    end = source.index("K_WORK_DEFINE(underglow_tick_work")
    effects = source[start:end]
    replace(effects, effects.replace("state.", "render_state->"))
    replace("static void zmk_rgb_underglow_tick(struct k_work *work) {", """static void zmk_rgb_underglow_tick(struct k_work *work) {
    bool alert = rgb_alert_active();
    render_state = alert ? &alert_state : &state;
#if IS_ENABLED(CONFIG_ZMK_RGB_UNDERGLOW_EXT_POWER)
    bool powered = rgb_awake && (state.on || alert);
    if (ext_power_get(ext_power) != powered) {
        int rc = powered ? ext_power_enable(ext_power) : ext_power_disable(ext_power);
        if (rc < 0) {
            LOG_ERR("Unable to switch RGB power: %d", rc);
        }
    }
#endif
    if (!rgb_awake || (!state.on && !alert)) {
        memset(pixels, 0, sizeof(pixels));
        led_strip_update_rgb(led_strip, pixels, STRIP_NUM_PIXELS);
        return;
    }""")
    replace("    int err = led_strip_update_rgb(led_strip, pixels, STRIP_NUM_PIXELS);", """    if (alert) {
        /* Upstream breathe ignores color.b; cap this overlay at 5% output. */
        for (int i = 0; i < STRIP_NUM_PIXELS; i++) {
            pixels[i].r = pixels[i].r * 5 / MAX(CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX, 1);
            pixels[i].g = 0;
            pixels[i].b = 0;
        }
    }
    int err = led_strip_update_rgb(led_strip, pixels, STRIP_NUM_PIXELS);""")
    replace("    if (!state.on) {\n        return;\n    }", """    if (!rgb_awake || (!state.on && !rgb_alert_active())) {
        k_timer_stop(timer);
        /* Queue one final dark frame when an alert or idle interval ends. */
    }""")
    replace("K_TIMER_DEFINE(underglow_tick, zmk_rgb_underglow_tick_handler, NULL);", """K_TIMER_DEFINE(underglow_tick, zmk_rgb_underglow_tick_handler, NULL);

static void refresh_rgb(void) {
    if (!IS_ENABLED(CONFIG_SHIELD_IMPRINT_DONGLE)) {
        k_timer_start(&underglow_tick, K_NO_WAIT, K_MSEC(50));
    }
}""")
    replace("            if (state.on) {\n                k_timer_start(&underglow_tick, K_NO_WAIT, K_MSEC(50));\n            }",
            "            refresh_rgb();")
    replace("    led_strip = DEVICE_DT_GET(STRIP_CHOSEN);", """#if !IS_ENABLED(CONFIG_SHIELD_IMPRINT_DONGLE)
    led_strip = DEVICE_DT_GET(STRIP_CHOSEN);
#endif""")
    replace("    if (state.on) {\n        k_timer_start(&underglow_tick, K_NO_WAIT, K_MSEC(50));\n    }",
            "    refresh_rgb();")
    # Physical device guards must not reject the dongle's state-only operations.
    source = source.replace("if (!led_strip)",
                            "if (!led_strip && !IS_ENABLED(CONFIG_SHIELD_IMPRINT_DONGLE))")
    replace("    k_timer_start(&underglow_tick, K_NO_WAIT, K_MSEC(50));\n\n    return zmk_rgb_underglow_save_state();",
            "    refresh_rgb();\n\n    return zmk_rgb_underglow_save_state();")
    start = source.index("static void zmk_rgb_underglow_off_handler")
    end = source.index("int zmk_rgb_underglow_off(void)")
    source = source[:start] + source[end:]
    # Power follows rendered activity/alerts, not mutations of user preferences.
    for operation in ("enable", "disable"):
        block_start = source.index("#if IS_ENABLED(CONFIG_ZMK_RGB_UNDERGLOW_EXT_POWER)",
                                   source.index(f"int zmk_rgb_underglow_{'on' if operation == 'enable' else 'off'}(void)"))
        block_end = source.index("#endif", block_start) + len("#endif")
        source = source[:block_start] + source[block_end:]
    replace("    k_work_submit_to_queue(zmk_workqueue_lowprio_work_q(), &underglow_off_work);\n\n    k_timer_stop(&underglow_tick);\n    state.on = false;",
            "    state.on = false;\n    refresh_rgb();")
    replace("    state.color = color;\n\n    return 0;",
            "    state.color = color;\n\n    return zmk_rgb_underglow_save_state();")
    start = source.index("struct rgb_underglow_sleep_state")
    end = source.index("static int rgb_underglow_event_listener")
    source = source[:start] + """static int rgb_underglow_auto_state(bool target_wake_state) {
    rgb_awake = target_wake_state;
    refresh_rgb();
    return 0;
}

""" + source[end:]
    replace("#include <stdlib.h>", "#include <stdlib.h>\n#include <string.h>")
    return source


if __name__ == "__main__":
    Path(sys.argv[2]).write_text(patch(Path(sys.argv[1]).read_text()))
