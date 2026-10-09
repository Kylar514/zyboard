zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)

zephyr_library()
zephyr_library_sources_ifdef(CONFIG_ZMK_IMPRINT_BATTERY_RGB src/battery_rgb.c)
zephyr_library_sources_ifdef(CONFIG_ZMK_IMPRINT_BATTERY_HID src/battery_hid.c)

# Keep upstream RGB behaviors; replace only their state/render implementation.
if(CONFIG_ZMK_RGB_UNDERGLOW)
  set(rgb_source ${APPLICATION_SOURCE_DIR}/src/rgb_underglow.c)
  set(rgb_fixed ${CMAKE_CURRENT_BINARY_DIR}/rgb_underglow.c)
  execute_process(
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_LIST_DIR}/fix_rgb.py ${rgb_source} ${rgb_fixed}
    RESULT_VARIABLE rgb_result
  )
  if(NOT rgb_result EQUAL 0)
    message(FATAL_ERROR "Imprint RGB compatibility patch failed; check upstream RGB changes")
  endif()
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${rgb_source} ${CMAKE_CURRENT_LIST_DIR}/fix_rgb.py)
  set_source_files_properties(${rgb_source} DIRECTORY ${APPLICATION_SOURCE_DIR} PROPERTIES HEADER_FILE_ONLY TRUE)
  target_sources(app PRIVATE ${rgb_fixed})
endif()
