#include <errno.h>

#include <zephyr/init.h>
#include <zephyr/kernel.h>

#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/rgb_underglow.h>

#define BATTERY_LOW_THRESHOLD 10
#define BATTERY_CRITICAL_THRESHOLD 5
#define BATTERY_ALERT_EFFECT 1
#define BATTERY_ALERT_COLOR ((struct zmk_led_hsb){.h = 0, .s = 100, .b = 5})

static struct k_work_delayable battery_alert_timeout;
static struct zmk_led_hsb saved_color;
static int saved_effect;
static bool saved_on;
static bool alert_active;
static bool battery_initialized;
static uint8_t previous_battery_level;

static void restore_battery_alert(struct k_work *work) {
    zmk_rgb_underglow_set_hsb(saved_color);
    zmk_rgb_underglow_select_effect(saved_effect);
    if (saved_on) {
        zmk_rgb_underglow_on();
    } else {
        zmk_rgb_underglow_off();
    }
    alert_active = false;
}

static void start_battery_alert(bool critical) {
    if (!alert_active) {
        saved_color = zmk_rgb_underglow_calc_hue(0);
        saved_effect = zmk_rgb_underglow_calc_effect(0);
        zmk_rgb_underglow_get_state(&saved_on);
        alert_active = true;
    }

    zmk_rgb_underglow_set_hsb(BATTERY_ALERT_COLOR);
    zmk_rgb_underglow_select_effect(BATTERY_ALERT_EFFECT);
    zmk_rgb_underglow_on();
    k_work_reschedule(&battery_alert_timeout,
                      K_SECONDS(critical ? 120 : 60));
}

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
        start_battery_alert(true);
    } else if (low) {
        start_battery_alert(false);
    }

    return 0;
}

static int battery_rgb_init(void) {
    k_work_init_delayable(&battery_alert_timeout, restore_battery_alert);
    return 0;
}

SYS_INIT(battery_rgb_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);

ZMK_LISTENER(imprint_battery_rgb, battery_rgb_listener);
ZMK_SUBSCRIPTION(imprint_battery_rgb, zmk_battery_state_changed);
