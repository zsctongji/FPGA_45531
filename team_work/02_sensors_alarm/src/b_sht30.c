#include "b_sensors.h"
#include <string.h>
static uint32_t error_bit(int rc) {
    return rc == COOP_ETIMEOUT ? COOP_ERROR_TIMEOUT :
           rc == COOP_ENACK ? COOP_ERROR_NACK : COOP_ERROR_BUS;
}
static int fail(b_sht30_t *d, int rc, uint32_t bits) {
    d->sample.valid_flags = 0;
    d->sample.error_bits = bits;
    d->state = 0;
    d->last_error = rc;
    return rc;
}
uint8_t b_sht30_crc(const uint8_t *data, size_t bytes) {
    uint8_t crc = 0xff;
    size_t i;
    unsigned b;
    for (i = 0; i < bytes; ++i) {
        crc ^= data[i];
        for (b = 0; b < 8; ++b)
            crc = (uint8_t)((crc & 0x80u) ? ((unsigned)crc << 1) ^ 0x31u : (unsigned)crc << 1);
    }
    return crc;
}
int b_sht30_init(b_sht30_t *d, const c3_hal_t *hal, uint8_t address7) {
    if (!d) return COOP_EINVAL;
    memset(d, 0, sizeof(*d));
    d->hal = hal;
    d->sample.abi_version = COOP_ABI_VERSION;
    if (address7 != 0x44 && address7 != 0x45) return COOP_EINVAL;
    d->address7 = address7;
    if ((c3_capabilities(hal) & (C3_CAP_TIME | C3_CAP_I2C)) != (C3_CAP_TIME | C3_CAP_I2C))
        return fail(d, COOP_ENOTSUP, COOP_ERROR_BUS);
    return COOP_OK;
}
static int command(b_sht30_t *d) {
    const uint8_t cmd[2] = {0x24, 0x00};
    int rc = c3_i2c_write_read(d->hal, C3_I2C_SENSOR_BUS, d->address7,
                              cmd, 2, NULL, 0, 20);
    ++d->attempts;
    if (rc != COOP_OK) return rc;
    rc = c3_now_ms(d->hal, &d->phase_ms);
    if (rc == COOP_OK) d->state = 1;
    return rc;
}
int b_sht30_start(b_sht30_t *d) {
    int rc;
    if (!d || (d->address7 != 0x44 && d->address7 != 0x45)) return COOP_EINVAL;
    if (d->state) return COOP_EBUSY;
    d->sample.valid_flags = 0;
    d->sample.error_bits = 0;
    d->sample.sample_id = ++d->next_id;
    d->sample.temperature_centi_c = 0;
    d->sample.humidity_centi_percent = 0;
    d->attempts = 0;
    rc = c3_now_ms(d->hal, &d->started_ms);
    if (rc != COOP_OK) return fail(d, rc, COOP_ERROR_BUS);
    rc = command(d);
    if (rc != COOP_OK) return fail(d, rc, error_bit(rc));
    return COOP_OK;
}
static int retry(b_sht30_t *d, int rc, uint32_t bits, uint32_t now) {
    d->sample.valid_flags = 0;
    d->sample.error_bits = bits;
    d->last_error = rc;
    if (d->attempts >= B_SHT_MAX_ATTEMPTS || rc == COOP_ENOTSUP)
        return fail(d, rc, bits);
    d->state = 2;
    d->phase_ms = now;
    return COOP_EBUSY;
}
int b_sht30_poll(b_sht30_t *d) {
    uint8_t raw[6];
    uint32_t now, t, h;
    int rc;
    if (!d) return COOP_EINVAL;
    if (!d->state) return COOP_ESTATE;
    rc = c3_now_ms(d->hal, &now);
    if (rc != COOP_OK) return fail(d, rc, COOP_ERROR_BUS);
    if ((uint32_t)(now - d->started_ms) >= B_SHT_DEADLINE_MS)
        return fail(d, COOP_ETIMEOUT, COOP_ERROR_TIMEOUT);
    if (d->state == 2) {
        if ((uint32_t)(now - d->phase_ms) < 5u) return COOP_EBUSY;
        rc = command(d);
        if (rc != COOP_OK) return retry(d, rc, error_bit(rc), now);
        return COOP_EBUSY;
    }
    if ((uint32_t)(now - d->phase_ms) < B_SHT_WAIT_MS) return COOP_EBUSY;
    rc = c3_i2c_write_read(d->hal, C3_I2C_SENSOR_BUS, d->address7, NULL, 0, raw, 6, 20);
    if (c3_now_ms(d->hal, &now) != COOP_OK) return fail(d, COOP_ENOTSUP, COOP_ERROR_BUS);
    if ((uint32_t)(now - d->started_ms) >= B_SHT_DEADLINE_MS)
        return fail(d, COOP_ETIMEOUT, COOP_ERROR_TIMEOUT);
    if (rc != COOP_OK) return retry(d, rc, error_bit(rc), now);
    if (b_sht30_crc(raw, 2) != raw[2] || b_sht30_crc(raw + 3, 2) != raw[5])
        return retry(d, COOP_EIO, COOP_ERROR_CRC, now);
    t = ((uint32_t)raw[0] << 8) | raw[1];
    h = ((uint32_t)raw[3] << 8) | raw[4];
    d->sample.temperature_centi_c = -4500 + (int32_t)((17500u * t + 32767u) / 65535u);
    d->sample.humidity_centi_percent = (10000u * h + 32767u) / 65535u;
    d->sample.timestamp_ms = now;
    d->sample.error_bits = 0;
    d->sample.valid_flags = COOP_SAMPLE_VALID;
    d->state = 0;
    d->last_error = COOP_OK;
    return COOP_OK;
}
int b_sht30_get(const b_sht30_t *d, coop_environment_t *out) {
    uint32_t now;
    int rc;
    if (!d || !out) return COOP_EINVAL;
    *out = d->sample;
    rc = c3_now_ms(d->hal, &now);
    if (rc != COOP_OK) { out->valid_flags = 0; out->error_bits |= COOP_ERROR_BUS; return rc; }
    if (out->valid_flags != COOP_SAMPLE_VALID || out->error_bits) return COOP_ESTATE;
    if ((uint32_t)(now - out->timestamp_ms) > COOP_ENV_MAX_LAG_MS) {
        out->valid_flags = 0;
        out->error_bits |= COOP_ERROR_TIMEOUT;
        return COOP_ETIMEOUT;
    }
    return COOP_OK;
}
