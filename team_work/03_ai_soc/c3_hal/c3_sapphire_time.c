#include "c3_hal.h"
#include "soc.h"
#include "clint.h"
#if SYSTEM_CLINT_HZ != 100000000
#error Verify the shared timer and update the integration contract before building
#endif
static uint32_t now(void *context) {
    (void)context;
    return (uint32_t)(clint_getTime(SYSTEM_CLINT_CTRL) / (SYSTEM_CLINT_HZ/1000u));
}
void c3_bind_sapphire_time(c3_hal_t *h) {
    h->context = 0;
    h->now_ms = now;
    h->i2c_write_read = 0;
    h->gpio_write = 0;
    h->checked_now_ms = 0;
}

