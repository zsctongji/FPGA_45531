#include "b_mlx_port.h"
#include "MLX90640_I2C_Driver.h"
#include <string.h>
static const c3_hal_t *port;
static uint32_t start_ms, budget, remaining;
static int last_error;
int b_mlx_session_begin(const c3_hal_t *hal, uint32_t ms, uint32_t calls) {
    uint32_t now;
    int rc;
    if (port) return COOP_EBUSY;
    if (!ms || ms >= 0x80000000u || !calls) return COOP_EINVAL;
    if ((c3_capabilities(hal) & (C3_CAP_TIME | C3_CAP_I2C)) != (C3_CAP_TIME | C3_CAP_I2C))
        return COOP_ENOTSUP;
    rc = c3_now_ms(hal, &now);
    if (rc != COOP_OK) return rc;
    port = hal; start_ms = now; budget = ms; remaining = calls; last_error = COOP_OK;
    return COOP_OK;
}
int b_mlx_session_end(void) {
    int rc = port ? last_error : COOP_ESTATE;
    port = NULL;
    return rc;
}
static int transfer(uint8_t address, const uint8_t *tx, uint32_t nt, uint8_t *rx, uint32_t nr) {
    uint32_t now, elapsed, timeout;
    int rc;
    if (!port) return -MLX90640_I2C_NACK_ERROR;
    if (last_error != COOP_OK) return -MLX90640_I2C_NACK_ERROR;
    rc = c3_now_ms(port, &now);
    if (rc != COOP_OK) { last_error = rc; return -MLX90640_I2C_NACK_ERROR; }
    elapsed = now - start_ms;
    if (!remaining || elapsed >= budget) {
        last_error = COOP_ETIMEOUT; return -MLX90640_I2C_NACK_ERROR;
    }
    timeout = budget - elapsed;
    if (timeout > 20) timeout = 20;
    --remaining;
    rc = c3_i2c_write_read(port, C3_I2C_SENSOR_BUS, address, tx, nt, rx, nr, timeout);
    if (rc == COOP_OK) {
        rc = c3_now_ms(port, &now);
        if (rc == COOP_OK && (uint32_t)(now - start_ms) >= budget) rc = COOP_ETIMEOUT;
    }
    if (rc != COOP_OK) { last_error = rc; return -MLX90640_I2C_NACK_ERROR; }
    return MLX90640_NO_ERROR;
}
void MLX90640_I2CInit(void) { /* Board backend owns initialization. */ }
void MLX90640_I2CFreqSet(int freq) { (void)freq; /* Configure clock in board backend. */ }
int MLX90640_I2CGeneralReset(void) {
    /* General-call 0x00 is outside C3 contract, and resets shared devices. */
    if (port) last_error = COOP_ENOTSUP;
    return -MLX90640_I2C_NACK_ERROR;
}
int MLX90640_I2CRead(uint8_t address, uint16_t reg, uint16_t words, uint16_t *data) {
    uint32_t done = 0, i;
    uint8_t raw[64], tx[2];
    if (!data || !words || address != 0x33 || (uint32_t)reg + words > 65536u) {
        if (port) last_error = COOP_EINVAL;
        return -MLX90640_I2C_NACK_ERROR;
    }
    while (done < words) {
        uint32_t chunk = words - done;
        uint16_t at = (uint16_t)(reg + done);
        if (chunk > 32) chunk = 32;
        tx[0] = (uint8_t)(at >> 8); tx[1] = (uint8_t)at;
        if (transfer(address, tx, 2, raw, chunk * 2) != MLX90640_NO_ERROR) {
            memset(data, 0, (size_t)words * sizeof(*data));
            return -MLX90640_I2C_NACK_ERROR;
        }
        for (i = 0; i < chunk; ++i) data[done + i] = (uint16_t)(((uint16_t)raw[i * 2] << 8) | raw[i * 2 + 1]);
        done += chunk;
    }
    return MLX90640_NO_ERROR;
}
int MLX90640_I2CWrite(uint8_t address, uint16_t reg, uint16_t value) {
    uint8_t tx[4] = {(uint8_t)(reg >> 8), (uint8_t)reg, (uint8_t)(value >> 8), (uint8_t)value};
    if (address != 0x33) { if (port) last_error = COOP_EINVAL; return -MLX90640_I2C_NACK_ERROR; }
    return transfer(address, tx, 4, NULL, 0);
}
