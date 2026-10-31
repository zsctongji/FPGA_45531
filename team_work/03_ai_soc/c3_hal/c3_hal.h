#ifndef C3_HAL_H
#define C3_HAL_H
#include "cooperation_v1.h"
#ifdef __cplusplus
extern "C" {
#endif
#define C3_CAP_TIME 1u
#define C3_HAL_INTERFACE_REV 2u
#define C3_CAP_I2C 2u
#define C3_CAP_GPIO 4u
#define C3_CAP_CHECKED_TIME 8u
#define C3_I2C_SENSOR_BUS 0u
#define C3_GPIO_ALARM_LED 0u
#define C3_GPIO_BUZZER_ENABLE 1u
typedef struct {
    void *context;
    uint32_t (*now_ms)(void *);
    /* 7-bit address, no R/W bit. Combined write/repeated-START/read, then STOP.
     * Callback must enforce timeout_ms, clean up STOP/bus state on failure,
     * and return COOP_OK only for the entire requested transaction. */
    int (*i2c_write_read)(void *, uint32_t bus, uint8_t address7,
                         const uint8_t *tx, uint32_t tx_bytes,
                         uint8_t *rx, uint32_t rx_bytes, uint32_t timeout_ms);
    /* Logical active 0/1, physical pin/polarity/PWM policy belongs to backend. */
    int (*gpio_write)(void *, uint32_t channel, uint32_t active);
    /* Optional checked clock; preferred over legacy now_ms. New binders must
     * initialize the whole struct. This is a C interface extension, not a
     * serialized coop_* ABI change. Errors leave the caller's result intact. */
    int (*checked_now_ms)(void *, uint32_t *);
} c3_hal_t;
uint32_t c3_capabilities(const c3_hal_t *hal);
int c3_now_ms(const c3_hal_t *hal, uint32_t *result);
int c3_i2c_write_read(const c3_hal_t *, uint32_t bus, uint8_t address7,
                      const uint8_t *, uint32_t, uint8_t *, uint32_t, uint32_t);
int c3_gpio_write(const c3_hal_t *, uint32_t channel, uint32_t active);
/* Actual current BSP binding: CLINT only. No invented GPIO/I2C registers. */
void c3_bind_sapphire_time(c3_hal_t *hal);
#ifdef __cplusplus
}
#endif
#endif

