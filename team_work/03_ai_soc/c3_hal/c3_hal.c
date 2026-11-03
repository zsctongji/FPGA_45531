#include "c3_hal.h"
uint32_t c3_capabilities(const c3_hal_t *h) {
    if (!h) return 0;
    return ((h->now_ms || h->checked_now_ms) ? C3_CAP_TIME : 0u) |
           (h->checked_now_ms ? C3_CAP_CHECKED_TIME : 0u) |
           (h->i2c_write_read ? C3_CAP_I2C : 0u) |
           (h->gpio_write ? C3_CAP_GPIO : 0u);
}
int c3_now_ms(const c3_hal_t *h, uint32_t *result) {
    if (!result) return COOP_EINVAL;
    if (!h) return COOP_ENOTSUP;
    if (h->checked_now_ms) {
        uint32_t value; int rc=h->checked_now_ms(h->context,&value);
        if(rc) return rc>0?COOP_EIO:rc;
        *result=value;return COOP_OK;
    }
    if (!h->now_ms) return COOP_ENOTSUP;
    *result = h->now_ms(h->context); return COOP_OK;
}
int c3_i2c_write_read(const c3_hal_t *h, uint32_t bus, uint8_t address,
                      const uint8_t *tx, uint32_t nt, uint8_t *rx, uint32_t nr,
                      uint32_t timeout) {
    if (address < 0x08 || address > 0x77 || (!nt && !nr) ||
        (nt && !tx) || (nr && !rx) || !timeout || timeout >= 0x80000000u)
        return COOP_EINVAL;
    if (!h || !h->i2c_write_read) return COOP_ENOTSUP;
    return h->i2c_write_read(h->context,bus,address,tx,nt,rx,nr,timeout);
}
int c3_gpio_write(const c3_hal_t *h,uint32_t channel,uint32_t active) {
    if (channel > C3_GPIO_BUZZER_ENABLE || active > 1u) return COOP_EINVAL;
    if (!h || !h->gpio_write) return COOP_ENOTSUP;
    return h->gpio_write(h->context,channel,active);
}

