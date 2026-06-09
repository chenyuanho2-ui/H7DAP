cmake_minimum_required(VERSION 3.22)

#
# This file is generated only once,
# and is not re-generated if converter is called multiple times.
#
# User is free to modify the file as much as necessary
#

# Setup compiler settings
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)


# Define the build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Debug")
endif()

# Set the project name
set(CMAKE_PROJECT_NAME daplink)

# Enable compile command to ease indexing with e.g. clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)

# Core project settings
project(${CMAKE_PROJECT_NAME})
message("Build type: " ${CMAKE_BUILD_TYPE})

# Enable CMake support for ASM and C languages
enable_language(C ASM)

# Create an executable object type
add_executable(${CMAKE_PROJECT_NAME})

# Add STM32CubeMX generated sources
add_subdirectory(cmake/stm32cubemx)

# Link directories setup
target_link_directories(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined library search paths
)

# Add sources to executable
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    # CherryDAP core
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/dap_main.c
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/DAP/Source/DAP.c
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/DAP/Source/SW_DP.c
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/DAP/Source/JTAG_DP.c
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/DAP/Source/SWO.c

    # CherryUSB stack core
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/core/usbd_core.c
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/class/cdc/usbd_cdc_acm.c

    # CherryUSB DWC2 port (STM32 USB OTG FS)
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/port/dwc2/usb_dc_dwc2.c
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/port/dwc2/usb_glue_st.c

    # CherryRB ringbuffer
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryRB/CherryRB-master/chry_ringbuffer.c

    # Bare-metal OSAL for CherryUSB
    ${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/usb_osal_none.c
)

# Add include paths (SYSTEM to keep them after HAL paths for correct include order)
target_include_directories(${CMAKE_PROJECT_NAME} SYSTEM PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/DAP/Include
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/DAP/Config
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/core
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/common
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/class/cdc
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/class/hub
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/class/hid
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/class/msc
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryUSB/port/dwc2
    ${CMAKE_CURRENT_SOURCE_DIR}/CherryDAP-master/CherryRB/CherryRB-master
)

# Add project symbols (macros)
target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined symbols
)

# Remove wrong libob.a library dependency when using cpp files
list(REMOVE_ITEM CMAKE_C_IMPLICIT_LINK_LIBRARIES ob)

# Add linked libraries
target_link_libraries(${CMAKE_PROJECT_NAME}
    stm32cubemx

    # Add user defined libraries
)
