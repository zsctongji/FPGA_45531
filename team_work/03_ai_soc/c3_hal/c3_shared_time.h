#ifndef C3_SHARED_TIME_H
#define C3_SHARED_TIME_H
#include "c2_driver.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Checked C2/C3 clock, unlike the legacy C1-only CLINT callback. All sensor and
 * image timestamps in the integrated SoC must use this reset epoch. Keep io and
 * its context alive. Binding requires a previously verified physical mapping. */
typedef struct { c2_io_t io; uint32_t bound; } c3_shared_clock_t;
int c3_shared_time_bind(c3_shared_clock_t *,const c2_io_t *);
int c3_shared_now_ms(void *clock,uint32_t *ms);
#ifdef __cplusplus
}
#endif
#endif
