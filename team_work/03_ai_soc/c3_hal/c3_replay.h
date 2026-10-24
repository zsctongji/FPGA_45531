#ifndef C3_REPLAY_H
#define C3_REPLAY_H
#include "c3_hal.h"
/* Explicitly synthetic, virtual-time I2C/GPIO backend for driver tests.
 * This is not a sensor model, a sensor driver, or a physical GPIO adapter. */
typedef struct {
    uint8_t address7;
    const uint8_t *tx, *rx;
    uint32_t tx_bytes, rx_bytes, delay_ms;
    int status;
} c3_replay_step_t;
typedef struct {
    const c3_replay_step_t *steps;
    uint32_t count, cursor, virtual_ms, gpio_active[2];
} c3_replay_t;
void c3_bind_replay(c3_hal_t *hal,c3_replay_t *replay);
#endif

