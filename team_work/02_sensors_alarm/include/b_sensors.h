#ifndef B_SENSORS_H
#define B_SENSORS_H
#include "c3_hal.h"
#include <stddef.h>
/* Single owner/task. All timestamps come from the C3 millisecond clock. */
#define B_SHT_WAIT_MS 16u
#define B_SHT_DEADLINE_MS 100u
#define B_SHT_MAX_ATTEMPTS 3u
typedef struct {
    const c3_hal_t *hal;
    uint8_t address7, state, attempts;
    uint32_t started_ms, phase_ms, next_id;
    int last_error;
    coop_environment_t sample;
} b_sht30_t;
uint8_t b_sht30_crc(const uint8_t *data, size_t bytes);
int b_sht30_init(b_sht30_t *, const c3_hal_t *, uint8_t address7);
int b_sht30_start(b_sht30_t *);
/* EBUSY: conversion or bounded retry pending; OK: new verified sample. */
int b_sht30_poll(b_sht30_t *);
int b_sht30_get(const b_sht30_t *, coop_environment_t *);

/* Assemble already-calibrated per-subpage Celsius values, NOT raw ADC values.
 * Real EEPROM extraction / CalculateTo are required before calling push.
 * Invalid/calibration failures invalidate the pair. No synthetic calibration. */
typedef struct {
    const c3_hal_t *hal;
    uint32_t first_ms, next_id;
    uint8_t seen, chess;
    int16_t staging[768];
    uint8_t bits[96];
    coop_thermal_t sample;
} b_thermal_pair_t;
int b_thermal_init(b_thermal_pair_t *, const c3_hal_t *);
void b_thermal_fault(b_thermal_pair_t *, uint32_t error_bits);
int b_thermal_push(b_thermal_pair_t *, uint8_t subpage, uint8_t chess,
                   const float celsius[768], const uint8_t bad_bits[96],
                   uint32_t calibration_ok);
int b_thermal_get(const b_thermal_pair_t *, coop_thermal_t *);
#endif
