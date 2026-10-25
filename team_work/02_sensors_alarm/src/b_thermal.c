#include "b_sensors.h"
#include <math.h>
#include <string.h>
int b_thermal_init(b_thermal_pair_t *d, const c3_hal_t *hal) {
    if (!d) return COOP_EINVAL;
    memset(d, 0, sizeof(*d));
    d->hal = hal;
    d->sample.abi_version = COOP_ABI_VERSION;
    return (c3_capabilities(hal) & C3_CAP_TIME) ? COOP_OK : COOP_ENOTSUP;
}
void b_thermal_fault(b_thermal_pair_t *d, uint32_t bits) {
    if (!d) return;
    d->seen = 0;
    memset(d->bits, 0, sizeof(d->bits));
    memset(&d->sample, 0, sizeof(d->sample));
    d->sample.abi_version = COOP_ABI_VERSION;
    d->sample.error_bits = bits ? bits : COOP_ERROR_BUS;
}
int b_thermal_push(b_thermal_pair_t *d, uint8_t sub, uint8_t chess,
                   const float celsius[768], const uint8_t bad[96], uint32_t calibrated) {
    uint32_t now, i, errors = 0;
    int rc;
    if (!d) return COOP_EINVAL;
    if (!celsius || !bad || sub > 1 || chess > 1 || calibrated > 1) {
        b_thermal_fault(d, COOP_ERROR_SUBFRAME); return COOP_EINVAL;
    }
    if (!calibrated) { b_thermal_fault(d, COOP_ERROR_CALIBRATION); return COOP_ESTATE; }
    rc = c3_now_ms(d->hal, &now);
    if (rc != COOP_OK) { b_thermal_fault(d, COOP_ERROR_BUS); return rc; }
    d->sample.valid_flags = 0;
    if (d->seen && ((uint32_t)(now - d->first_ms) > COOP_THERMAL_MAX_LAG_MS || d->chess != chess)) {
        b_thermal_fault(d, COOP_ERROR_SUBFRAME); return COOP_ESTATE;
    }
    /* Same subpage again: replace the partial sample; never pair with itself. */
    if (!d->seen || (d->seen & (1u << sub))) {
        d->seen = 0;
        d->first_ms = now;
        d->chess = chess;
        memset(d->bits, 0, sizeof(d->bits));
    }
    for (i = 0; i < 768; ++i) {
        uint32_t page = (i / 32u) & 1u;
        float scaled;
        long rounded;
        if (chess) page ^= i & 1u;
        if (page != sub) continue;
        d->staging[i] = 0;
        if ((bad[i / 8] & (1u << (i % 8))) || !isfinite(celsius[i])) continue;
        scaled = celsius[i] * 100.0f;
        if (!isfinite(scaled) || scaled < -32768.0f || scaled > 32767.0f) continue;
        rounded = lroundf(scaled);
        if (rounded < -32768 || rounded > 32767) continue;
        d->staging[i] = (int16_t)rounded;
        d->bits[i / 8] |= (uint8_t)(1u << (i % 8));
    }
    d->seen |= (uint8_t)(1u << sub);
    if (d->seen != 3) return COOP_EBUSY;
    d->seen = 0;
    memcpy(d->sample.temperature_centi_c, d->staging, sizeof(d->staging));
    memcpy(d->sample.pixel_valid_bits, d->bits, sizeof(d->bits));
    for (i = 0; i < 96; ++i) if (d->bits[i] != 0xff) errors |= COOP_ERROR_PIXEL_QUALITY;
    d->sample.sample_id = ++d->next_id;
    /* Older subpage timestamp conservatively accounts for the full pair's age. */
    d->sample.timestamp_ms = d->first_ms;
    d->sample.error_bits = errors;
    d->sample.valid_flags = COOP_SAMPLE_COMPLETE | COOP_SAMPLE_CONVERTED;
    if (!errors) d->sample.valid_flags |= COOP_SAMPLE_QUALITY;
    return errors ? COOP_EIO : COOP_OK;
}
int b_thermal_get(const b_thermal_pair_t *d, coop_thermal_t *out) {
    uint32_t now;
    int rc;
    if (!d || !out) return COOP_EINVAL;
    *out = d->sample;
    rc = c3_now_ms(d->hal, &now);
    if (rc != COOP_OK) { out->valid_flags = 0; out->error_bits |= COOP_ERROR_BUS; return rc; }
    if (out->valid_flags != COOP_SAMPLE_VALID || out->error_bits) return COOP_ESTATE;
    if ((uint32_t)(now - out->timestamp_ms) > COOP_THERMAL_MAX_LAG_MS) {
        out->valid_flags = 0; out->error_bits |= COOP_ERROR_TIMEOUT; return COOP_ETIMEOUT;
    }
    return COOP_OK;
}
