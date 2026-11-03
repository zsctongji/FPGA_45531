#ifndef C3_THERMAL_PUBLISH_H
#define C3_THERMAL_PUBLISH_H
#include "c3_hal.h"
#define C3_THERMAL_STRICT 0u
#define C3_THERMAL_ALLOW_BAD_620 1u
#define C3_THERMAL_QUALITY_MASKED 1u
#define C3_THERMAL_QUALITY_FULL 2u
typedef struct {uint32_t valid_pixels,quality,age_ms;} c3_thermal_quality_t;
/* Immutable snapshot, same shared-clock epoch as hal. No resampling, bad-pixel
 * interpolation or promotion of flags/errors. Failure never changes output.
 * The optional degraded policy is deliberately limited to B's audited pixel620.
 * Caller must serialize publication, and must not treat MASKED as FULL. */
int c3_publish_thermal(const c3_hal_t *,const coop_thermal_t *,uint32_t policy,
                      coop_thermal_t *,c3_thermal_quality_t *);
#endif
