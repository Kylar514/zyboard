#include <errno.h>

#include <zephyr/device.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/usb/class/usb_hid.h>

#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>

LOG_MODULE_REGISTER(zyboard_battery_hid, CONFIG_ZMK_LOG_LEVEL);

#define BATTERY_REPORT_ID 1
#define BATTERY_UNKNOWN 0xFF
#define BATTERY_SLOT_COUNT 2

static const uint8_t report_descriptor[] = {
    0x06, 0x00, 0xFF,       /* Usage Page (vendor defined) */
    0x09, 0x01,             /* Usage (split battery levels) */
    0xA1, 0x01,             /* Collection (Application) */
    0x85, BATTERY_REPORT_ID,/* Report ID */
    0x15, 0x00,             /* Logical Minimum (0) */
    0x26, 0xFF, 0x00,       /* Logical Maximum (255) */
    0x75, 0x08,             /* Report Size (8 bits) */
    0x95, 0x01,             /* Report Count (1) */
    0x09, 0x01, 0x81, 0x02, /* Usage 1: peripheral slot 1 */
    0x09, 0x02, 0x81, 0x02, /* Usage 2: peripheral slot 2 */
    0xC0,                   /* End Collection */
};

static const struct device *hid_dev;
static struct k_work_delayable report_work;
static struct k_spinlock battery_lock;
static struct k_sem report_ready;
static uint8_t battery_levels[BATTERY_SLOT_COUNT] = {BATTERY_UNKNOWN, BATTERY_UNKNOWN};

static void report_ready_cb(const struct device *dev) {
    ARG_UNUSED(dev);
    k_sem_give(&report_ready);
}

static const struct hid_ops hid_ops = {
    .int_in_ready = report_ready_cb,
};

static void send_battery_report(struct k_work *work) {
    ARG_UNUSED(work);
    uint8_t report[] = {BATTERY_REPORT_ID, BATTERY_UNKNOWN, BATTERY_UNKNOWN};
    k_spinlock_key_t key = k_spin_lock(&battery_lock);
    report[1] = battery_levels[0];
    report[2] = battery_levels[1];
    k_spin_unlock(&battery_lock, key);

    if (hid_dev != NULL && k_sem_take(&report_ready, K_MSEC(100)) == 0) {
        if (hid_int_ep_write(hid_dev, report, sizeof(report), NULL) != 0) {
            k_sem_give(&report_ready);
        }
    }

    /* Repeat so a reader started after boot gets the latest levels promptly. */
    k_work_reschedule(&report_work, K_SECONDS(5));
}

static int battery_listener(const zmk_event_t *eh) {
    const struct zmk_peripheral_battery_state_changed *event =
        as_zmk_peripheral_battery_state_changed(eh);
    if (event == NULL) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    if (event->source < BATTERY_SLOT_COUNT) {
        k_spinlock_key_t key = k_spin_lock(&battery_lock);
        battery_levels[event->source] = event->state_of_charge;
        k_spin_unlock(&battery_lock, key);
        k_work_reschedule(&report_work, K_NO_WAIT);
    }

    return ZMK_EV_EVENT_BUBBLE;
}

static int battery_hid_init(void) {
    k_sem_init(&report_ready, 1, 1);
    k_work_init_delayable(&report_work, send_battery_report);

    hid_dev = device_get_binding("HID_1");
    if (hid_dev == NULL) {
        LOG_ERR("Unable to locate battery HID interface HID_1");
        return -ENODEV;
    }

    usb_hid_register_device(hid_dev, report_descriptor, sizeof(report_descriptor), &hid_ops);
    int err = usb_hid_init(hid_dev);
    if (err != 0) {
        LOG_ERR("Unable to initialize battery HID interface: %d", err);
        hid_dev = NULL;
        return err;
    }

    k_work_reschedule(&report_work, K_NO_WAIT);
    return 0;
}

SYS_INIT(battery_hid_init, APPLICATION, 91);

ZMK_LISTENER(zyboard_battery_hid, battery_listener);
ZMK_SUBSCRIPTION(zyboard_battery_hid, zmk_peripheral_battery_state_changed);
