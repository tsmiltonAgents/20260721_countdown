#pragma once
/* Countdown target: 2026-10-10 12:00:00 LOCAL time.
 * The RTC runs in local time, set at flash time from the build timestamp
 * (see Makefile: BUILD_LOCAL_* macros). Both flash date (summer 2026) and
 * the target fall inside British Summer Time (ends 25 Oct 2026), so local
 * time has no DST discontinuity before the target. */
#define TARGET_Y 2026
#define TARGET_MO 10
#define TARGET_D 10
#define TARGET_H 12
#define TARGET_MIN 0

/* How long the display stays on after a button press (ms) */
#define DISPLAY_ON_MS 8000u
/* Per-digit dwell during multiplexing (ms): 4 digits -> ~125 Hz frame */
#define DIGIT_DWELL_MS 2u

/* --- Pin map (matches hw/scripts/gen_sch.py — single source of truth is
 * the PINMAP table in that file; keep in sync, checked by review) ---
 * Segments A..G,DP drive GPIOA pins SEG_PINS[i] (source current, active high
 * for common-cathode display).
 * Digits 1..4 sink through DIG_PORT/DIG_PIN (active low output).
 * Button: PB3 to GND, internal pull-up, EXTI3 falling edge.
 */
#define SEGA_PIN 0 /* PA0 */
#define SEGB_PIN 1 /* PA1 */
#define SEGC_PIN 2 /* PA2 */
#define SEGD_PIN 3 /* PA3 */
#define SEGE_PIN 4 /* PA4 */
#define SEGF_PIN 5 /* PA5 */
#define SEGG_PIN 6 /* PA6 */
#define SEGDP_PIN 7 /* PA7 */

/* digit commons: entries are (GPIO, pin). Digit 1 = leftmost. */
#define DIG1_PORT GPIOB
#define DIG1_PIN 0
#define DIG2_PORT GPIOB
#define DIG2_PIN 1
#define DIG3_PORT GPIOA
#define DIG3_PIN 8
#define DIG4_PORT GPIOA
#define DIG4_PIN 9

#define BTN_PORT GPIOB
#define BTN_PIN 3
