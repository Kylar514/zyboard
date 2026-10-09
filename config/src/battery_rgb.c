#include <errno.h>

#include <zephyr/kernel.h>

#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>

#define BATTERY_LOW_THRESHOLD 10
#define BATTERY_CRITICAL_THRESHOLD 5
void imprint_rgb_battery_alert(uint32_t seconds);

static bool battery_initialized;
static uint8_t previous_battery_level;

static int battery_rgb_listener(const zmk_event_t *eh) {
    const struct zmk_battery_state_changed *event = as_zmk_battery_state_changed(eh);
    if (event == NULL) {
        return -ENOTSUP;
    }

    uint8_t level = event->state_of_charge;
    bool critical = level <= BATTERY_CRITICAL_THRESHOLD &&
                    (!battery_initialized || previous_battery_level > BATTERY_CRITICAL_THRESHOLD);
    bool low = level <= BATTERY_LOW_THRESHOLD &&
               (!battery_initialized || previous_battery_level > BATTERY_LOW_THRESHOLD);
    previous_battery_level = level;
    battery_initialized = true;

    if (critical) {
        imprint_rgb_battery_alert(120);
    } else if (low) {
        imprint_rgb_battery_alert(60);
    }

    return 0;
}

ZMK_LISTENER(imprint_battery_rgb, battery_rgb_listener);
ZMK_SUBSCRIPTION(imprint_battery_rgb, zmk_battery_state_changed);
