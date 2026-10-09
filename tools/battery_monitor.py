#!/usr/bin/env python3
"""Read the Imprint dongle's two-slot battery HID report on Linux."""

import argparse
import os
from pathlib import Path
import sys

REPORT_ID = 1
UNKNOWN = 0xFF
REPORT_DESCRIPTOR_MARKER = bytes((0x06, 0x00, 0xFF, 0x09, 0x01))


def decode_report(report):
    if len(report) != 3 or report[0] != REPORT_ID:
        return None
    levels = report[1:]
    if any(level != UNKNOWN and level > 100 for level in levels):
        return None
    return tuple(None if level == UNKNOWN else level for level in levels)


def find_device():
    for node in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
        try:
            descriptor = (node / "device/report_descriptor").read_bytes()
        except OSError:
            continue
        if REPORT_DESCRIPTOR_MARKER in descriptor:
            return Path("/dev") / node.name
    return None


def show_levels(levels):
    values = [f"{level}%" if level is not None else "unknown" for level in levels]
    print(f"Peripheral slot 1: {values[0]}    Peripheral slot 2: {values[1]}", flush=True)


def self_test():
    assert decode_report(bytes((REPORT_ID, 72, 31))) == (72, 31)
    assert decode_report(bytes((REPORT_ID, 0xFF, 5))) == (None, 5)
    assert decode_report(bytes((2, 72, 31))) is None
    assert decode_report(bytes((REPORT_ID, 101, 31))) is None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", help="hidraw device, e.g. /dev/hidraw4")
    parser.add_argument("--self-test", action="store_true", help="check report decoding and exit")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("battery report checks passed")
        return 0

    device = args.device or find_device()
    if device is None:
        parser.error("battery HID not found; pass its /dev/hidrawN path with --device")

    try:
        fd = os.open(device, os.O_RDONLY)
    except OSError as error:
        print(f"Cannot open {device}: {error}. Install the udev rule, then replug the dongle.", file=sys.stderr)
        return 1

    print(f"Reading {device}; slot order follows BLE pairing order. Press Ctrl+C to stop.")
    try:
        while True:
            report = os.read(fd, 64)
            levels = decode_report(report)
            if levels is not None:
                show_levels(levels)
    except KeyboardInterrupt:
        return 0
    finally:
        os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main())
