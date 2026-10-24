#include "c3_replay.h"
#include <string.h>
static uint32_t tick(void *p) { return ((c3_replay_t *)p)->virtual_ms; }
static int transfer(void *p,uint32_t bus,uint8_t addr,const uint8_t *tx,uint32_t nt,
                     uint8_t *rx,uint32_t nr,uint32_t timeout) {
    c3_replay_t *r=(c3_replay_t *)p;
    const c3_replay_step_t *s;
    if(bus!=C3_I2C_SENSOR_BUS) return COOP_ENOTSUP;
    if(r->cursor>=r->count || !r->steps) return COOP_ENACK;
    s=r->steps+r->cursor;
    if(addr!=s->address7) return COOP_ENACK;
    if(nt!=s->tx_bytes || nr!=s->rx_bytes ||
       (nt && (!s->tx || memcmp(tx,s->tx,nt)))) return COOP_EIO;
    ++r->cursor;
    if(s->delay_ms>timeout) { r->virtual_ms+=timeout; return COOP_ETIMEOUT; }
    r->virtual_ms+=s->delay_ms;
    if(s->status!=COOP_OK) return s->status;
    if(nr && !s->rx) return COOP_EIO;
    if(nr) memcpy(rx,s->rx,nr);
    return COOP_OK;
}
static int gpio(void *p,uint32_t channel,uint32_t active) {
    c3_replay_t *r=(c3_replay_t *)p;
    if(channel>1 || active>1) return COOP_EINVAL;
    r->gpio_active[channel]=active; return COOP_OK;
}
void c3_bind_replay(c3_hal_t *h,c3_replay_t *r) {
    h->context=r; h->now_ms=tick; h->i2c_write_read=transfer; h->gpio_write=gpio;
}

