/*
 * Copyright (c) 2013-2021 ARM Limited. All rights reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the License); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an AS IS BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * ----------------------------------------------------------------------
 *
 * Project:      CMSIS-DAP Configuration for STM32H750XBH6 DAPLink
 *
 *---------------------------------------------------------------------------*/

#ifndef __DAP_CONFIG_H__
#define __DAP_CONFIG_H__

#include "stdint.h"
#include "stm32h7xx_hal.h"

#ifndef   __STATIC_INLINE
#define __STATIC_INLINE                        static inline
#endif
#ifndef   __STATIC_FORCEINLINE
#define __STATIC_FORCEINLINE                   __attribute__((always_inline)) static inline
#endif
#ifndef __WEAK
#define __WEAK __attribute__((weak))
#endif

//**************************************************************************************************
//  Debug Unit Information
//**************************************************************************************************

/// Processor Clock: H7 CPU runs at 480MHz (SYSCLK=480MHz, D1CPRE=/1)
#define CPU_CLOCK               480000000U

/// I/O Port write cycles: STM32H7 GPIO write via BSRR takes ~2 cycles
#define IO_PORT_WRITE_CYCLES    2U

/// SWD available
#define DAP_SWD                 1
/// JTAG disabled (SWD-only for now)
#define DAP_JTAG                0
/// Max JTAG devices on scan chain (unused if JTAG=0)
#define DAP_JTAG_DEV_CNT        8U

/// Default port mode: 1 = SWD
#define DAP_DEFAULT_PORT        1U
/// Default SWD/JTAG clock frequency in Hz
#define DAP_DEFAULT_SWJ_CLOCK   1000000U

/// Packet size for Full-Speed USB (max 64)
#define DAP_PACKET_SIZE         64U
/// Number of packet buffers
#define DAP_PACKET_COUNT        8U

/// SWO UART trace: disabled for now
#define SWO_UART                0
#define SWO_UART_DRIVER         0
#define SWO_UART_MAX_BAUDRATE   10000000U
/// SWO Manchester: disabled
#define SWO_MANCHESTER          0
#define SWO_BUFFER_SIZE         4096U
#define SWO_STREAM              0

/// Timestamp clock: DWT runs at CPU frequency
#define TIMESTAMP_CLOCK         480000000U

/// UART Communication Port: disabled (USB-CDC handles this)
#define DAP_UART                0
#define DAP_UART_DRIVER         1
#define DAP_UART_RX_BUFFER_SIZE 1024U
#define DAP_UART_TX_BUFFER_SIZE 1024U
#define DAP_UART_USB_COM_PORT   0

/// Target not fixed
#define TARGET_FIXED            0
#define TARGET_DEVICE_VENDOR    "Arm"
#define TARGET_DEVICE_NAME      "Cortex-M"
#define TARGET_BOARD_VENDOR     "Arm"
#define TARGET_BOARD_NAME       "Arm board"

#if TARGET_FIXED != 0
#include <string.h>
static const char TargetDeviceVendor [] = TARGET_DEVICE_VENDOR;
static const char TargetDeviceName   [] = TARGET_DEVICE_NAME;
static const char TargetBoardVendor  [] = TARGET_BOARD_VENDOR;
static const char TargetBoardName    [] = TARGET_BOARD_NAME;
#endif

//**************************************************************************************************
//  Identity Strings
//**************************************************************************************************

__STATIC_INLINE uint8_t DAP_GetVendorString (char *str) {
  (void)str;
  return (0U);
}

__STATIC_INLINE uint8_t DAP_GetProductString (char *str) {
  (void)str;
  return (0U);
}

__STATIC_INLINE uint8_t DAP_GetSerNumString (char *str) {
  (void)str;
  return (0U);
}

__STATIC_INLINE uint8_t DAP_GetTargetDeviceVendorString (char *str) {
#if TARGET_FIXED != 0
  uint8_t len;
  strcpy(str, TargetDeviceVendor);
  len = (uint8_t)(strlen(TargetDeviceVendor) + 1U);
  return (len);
#else
  (void)str;
  return (0U);
#endif
}

__STATIC_INLINE uint8_t DAP_GetTargetDeviceNameString (char *str) {
#if TARGET_FIXED != 0
  uint8_t len;
  strcpy(str, TargetDeviceName);
  len = (uint8_t)(strlen(TargetDeviceName) + 1U);
  return (len);
#else
  (void)str;
  return (0U);
#endif
}

__STATIC_INLINE uint8_t DAP_GetTargetBoardVendorString (char *str) {
#if TARGET_FIXED != 0
  uint8_t len;
  strcpy(str, TargetBoardVendor);
  len = (uint8_t)(strlen(TargetBoardVendor) + 1U);
  return (len);
#else
  (void)str;
  return (0U);
#endif
}

__STATIC_INLINE uint8_t DAP_GetTargetBoardNameString (char *str) {
#if TARGET_FIXED != 0
  uint8_t len;
  strcpy(str, TargetBoardName);
  len = (uint8_t)(strlen(TargetBoardName) + 1U);
  return (len);
#else
  (void)str;
  return (0U);
#endif
}

__STATIC_INLINE uint8_t DAP_GetProductFirmwareVersionString (char *str) {
  (void)str;
  return (0U);
}


//**************************************************************************************************
//  Pin Mapping
//**************************************************************************************************
//
//  SWCLK  = PD11
//  SWDIO  = PD12
//  nRESET = PD13
//  LED    = PC13 (active low)
//
//  TDO/TDI/nTRST are not used in SWD-only mode.

#define PORTD_BSRR  GPIOD->BSRR
#define PORTD_IDR   GPIOD->IDR
#define PORTD_MODER GPIOD->MODER
#define PORTD_ODR   GPIOD->ODR

#define PORTC_BSRR  GPIOC->BSRR

#define SWCLK_PIN   11U
#define SWDIO_PIN   12U
#define RESET_PIN   13U
#define LED_PIN     13U

//**************************************************************************************************
//  Port Setup
//**************************************************************************************************

__STATIC_INLINE void PORT_JTAG_SETUP (void) {
  /* Not used in SWD-only mode */
}

__STATIC_INLINE void PORT_SWD_SETUP (void) {
  /* Pins are already configured by MX_GPIO_Init().
   * Ensure SWCLK and nRESET are high, SWDIO in high-Z (input). */
  PORTD_BSRR = (1UL << SWCLK_PIN);      /* SWCLK = HIGH */
  PORTD_BSRR = (1UL << RESET_PIN);      /* nRESET = HIGH */
  PORTD_MODER &= ~(3UL << (SWDIO_PIN * 2));  /* SWDIO = input */
}

__STATIC_INLINE void PORT_OFF (void) {
  /* Set all pins to input (High-Z) */
  PORTD_MODER &= ~((3UL << (SWCLK_PIN * 2)) |
                   (3UL << (SWDIO_PIN * 2)) |
                   (3UL << (RESET_PIN * 2)));
}

//**************************************************************************************************
//  SWCLK/TCK
//**************************************************************************************************

__STATIC_FORCEINLINE uint32_t PIN_SWCLK_TCK_IN (void) {
  return ((PORTD_IDR >> SWCLK_PIN) & 1UL);
}

__STATIC_FORCEINLINE void PIN_SWCLK_TCK_SET (void) {
  PORTD_BSRR = (1UL << SWCLK_PIN);
}

__STATIC_FORCEINLINE void PIN_SWCLK_TCK_CLR (void) {
  PORTD_BSRR = (1UL << (SWCLK_PIN + 16U));
}

//**************************************************************************************************
//  SWDIO/TMS
//**************************************************************************************************

__STATIC_FORCEINLINE uint32_t PIN_SWDIO_TMS_IN (void) {
  return ((PORTD_IDR >> SWDIO_PIN) & 1UL);
}

__STATIC_FORCEINLINE void PIN_SWDIO_TMS_SET (void) {
  PORTD_BSRR = (1UL << SWDIO_PIN);
}

__STATIC_FORCEINLINE void PIN_SWDIO_TMS_CLR (void) {
  PORTD_BSRR = (1UL << (SWDIO_PIN + 16U));
}

//*** SWDIO fast functions (SWD mode only) ***

__STATIC_FORCEINLINE uint32_t PIN_SWDIO_IN (void) {
  return ((PORTD_IDR >> SWDIO_PIN) & 1UL);
}

__STATIC_FORCEINLINE void PIN_SWDIO_OUT (uint32_t bit) {
  if (bit) {
    PORTD_BSRR = (1UL << SWDIO_PIN);
  } else {
    PORTD_BSRR = (1UL << (SWDIO_PIN + 16U));
  }
}

__STATIC_FORCEINLINE void PIN_SWDIO_OUT_ENABLE (void) {
  PORTD_MODER = (PORTD_MODER & ~(3UL << (SWDIO_PIN * 2))) | (1UL << (SWDIO_PIN * 2));
}

__STATIC_FORCEINLINE void PIN_SWDIO_OUT_DISABLE (void) {
  PORTD_MODER &= ~(3UL << (SWDIO_PIN * 2));
}

//**************************************************************************************************
//  TDI (not used in SWD mode)
//**************************************************************************************************

__STATIC_FORCEINLINE uint32_t PIN_TDI_IN (void) {
  return (0U);
}

__STATIC_FORCEINLINE void PIN_TDI_OUT (uint32_t bit) {
  (void)bit;
}

//**************************************************************************************************
//  TDO (not used in SWD mode)
//**************************************************************************************************

__STATIC_FORCEINLINE uint32_t PIN_TDO_IN (void) {
  return (0U);
}

//**************************************************************************************************
//  nTRST (not used)
//**************************************************************************************************

__STATIC_FORCEINLINE uint32_t PIN_nTRST_IN (void) {
  return (0U);
}

__STATIC_FORCEINLINE void PIN_nTRST_OUT (uint32_t bit) {
  (void)bit;
}

//**************************************************************************************************
//  nRESET
//**************************************************************************************************

__STATIC_FORCEINLINE uint32_t PIN_nRESET_IN (void) {
  return ((PORTD_IDR >> RESET_PIN) & 1UL);
}

__STATIC_FORCEINLINE void PIN_nRESET_OUT (uint32_t bit) {
  if (bit) {
    PORTD_BSRR = (1UL << RESET_PIN);
  } else {
    PORTD_BSRR = (1UL << (RESET_PIN + 16U));
  }
}


//**************************************************************************************************
//  LEDs
//**************************************************************************************************
//
//  PC13 LED is active-low: BSRR[13] = HIGH (LED OFF), BSRR[13+16] = LOW (LED ON)
//  bit=1 means LED ON (connected/running), bit=0 means LED OFF

__STATIC_INLINE void LED_CONNECTED_OUT (uint32_t bit) {
  if (bit) {
    PORTC_BSRR = (1UL << (LED_PIN + 16U));  /* BR = LOW = LED ON */
  } else {
    PORTC_BSRR = (1UL << LED_PIN);          /* BS = HIGH = LED OFF */
  }
}

__STATIC_INLINE void LED_RUNNING_OUT (uint32_t bit) {
  if (bit) {
    PORTC_BSRR = (1UL << (LED_PIN + 16U));  /* BR = LOW = LED ON */
  } else {
    PORTC_BSRR = (1UL << LED_PIN);          /* BS = HIGH = LED OFF */
  }
}


//**************************************************************************************************
//  Timestamp
//**************************************************************************************************

__STATIC_INLINE uint32_t TIMESTAMP_GET (void) {
  return (DWT->CYCCNT);
}


//**************************************************************************************************
//  Initialization
//**************************************************************************************************

__STATIC_INLINE void DAP_SETUP (void) {
  /* GPIOs are initialized by MX_GPIO_Init(). Just set default states. */
  PORTD_BSRR = (1UL << SWCLK_PIN);     /* SWCLK HIGH */
  PORTD_BSRR = (1UL << SWDIO_PIN);     /* SWDIO HIGH */
  PORTD_BSRR = (1UL << RESET_PIN);     /* nRESET HIGH */
  PORTC_BSRR = (1UL << LED_PIN);       /* LED OFF */
  PIN_SWDIO_OUT_DISABLE();             /* SWDIO = input */
}

__STATIC_INLINE uint8_t RESET_TARGET (void) {
  return (0U);
}

#endif /* __DAP_CONFIG_H__ */
