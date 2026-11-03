#ifndef B_ALARM_H
#define B_ALARM_H
#include "c3_hal.h"
typedef struct {
    const c3_hal_t *hal;
    uint32_t started_ms, max_on_ms, led, buzzer;
    uint8_t active, inhibited;
} b_alarm_t;
/* Output policy only: C owns detection/fusion. max_on_ms is a reviewed product
 * policy, 1..2^31-1 ms. After timeout/fault clear(false) before rearming. */
int b_alarm_init(b_alarm_t *, const c3_hal_t *, uint32_t max_on_ms);
int b_alarm_request(b_alarm_t *, uint32_t active);
/* Service regularly. LED on while active, active buzzer 250ms on/750ms off. */
int b_alarm_poll(b_alarm_t *);
#endif
