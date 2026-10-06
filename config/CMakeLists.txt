zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)

zephyr_library()
zephyr_library_sources_ifdef(CONFIG_ZMK_IMPRINT_BATTERY_RGB src/battery_rgb.c)
