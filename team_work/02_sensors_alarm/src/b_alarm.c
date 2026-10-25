#include "b_alarm.h"
#include <string.h>
static int off(b_alarm_t *d) {
    int a = c3_gpio_write(d->hal, C3_GPIO_ALARM_LED, 0);
    int b = c3_gpio_write(d->hal, C3_GPIO_BUZZER_ENABLE, 0);
    /* If a write failed the physical state remains unknown; don't claim off. */
    d->led = a == COOP_OK ? 0u : 2u;
    d->buzzer = b == COOP_OK ? 0u : 2u;
    d->active = 0;
    if (a != COOP_OK || b != COOP_OK) d->inhibited = 1;
    return a != COOP_OK ? a : b;
}
int b_alarm_init(b_alarm_t *d, const c3_hal_t *hal, uint32_t max_on_ms) {
    if (!d) return COOP_EINVAL;
    memset(d, 0, sizeof(*d));
    d->hal = hal;
    d->inhibited = 1;
    if (!max_on_ms || max_on_ms >= 0x80000000u) return COOP_EINVAL;
    d->max_on_ms = max_on_ms;
    { int rc = off(d);
      if (rc != COOP_OK) return rc;
      if (!(c3_capabilities(hal) & C3_CAP_TIME)) return COOP_ENOTSUP;
    }
    d->inhibited = 0;
    return COOP_OK;
}
int b_alarm_request(b_alarm_t *d, uint32_t active) {
    int rc;
    if (!d || active > 1) return COOP_EINVAL;
    if (!active) {
        rc = off(d);
        if (rc == COOP_OK) d->inhibited = 0;
        return rc;
    }
    if (d->inhibited || !d->max_on_ms) return COOP_ESTATE;
    if (d->active) return COOP_OK;
    rc = c3_now_ms(d->hal, &d->started_ms);
    if (rc != COOP_OK) { d->inhibited = 1; (void)off(d); return rc; }
    d->active = 1;
    return b_alarm_poll(d);
}
int b_alarm_poll(b_alarm_t *d) {
    uint32_t now, age, buzzer;
    int rc;
    if (!d) return COOP_EINVAL;
    if (!d->active) return d->inhibited ? COOP_ESTATE : COOP_OK;
    rc = c3_now_ms(d->hal, &now);
    if (rc != COOP_OK) { d->inhibited = 1; (void)off(d); return rc; }
    age = now - d->started_ms;
    if (age >= d->max_on_ms) {
        d->inhibited = 1;
        rc = off(d);
        return rc == COOP_OK ? COOP_ETIMEOUT : rc;
    }
    buzzer = (age % 1000u) < 250u;
    rc = COOP_OK;
    if (d->led != 1) rc = c3_gpio_write(d->hal, C3_GPIO_ALARM_LED, 1);
    if (rc == COOP_OK && d->buzzer != buzzer)
        rc = c3_gpio_write(d->hal, C3_GPIO_BUZZER_ENABLE, buzzer);
    if (rc != COOP_OK) { d->inhibited = 1; (void)off(d); return rc; }
    d->led = 1;
    d->buzzer = buzzer;
    return COOP_OK;
}
