#include "c3_peripheral.h"
#include <string.h>
#include <stdint.h>
static int rd(c3_peripheral_t *p,uint32_t off,uint32_t *v) {
    int rc=p->io.read32(p->io.context,C3_PAGE+off,v);return rc>0?COOP_EIO:rc;
}
static int wr(c3_peripheral_t *p,uint32_t off,uint32_t v) {
    int rc;p->io.barrier(p->io.context);
    rc=p->io.write32(p->io.context,C3_PAGE+off,v);p->io.barrier(p->io.context);
    return rc>0?COOP_EIO:rc;
}
static void abort_bus(c3_peripheral_t *p) {
    (void)wr(p,C3_P_COMMAND,64);(void)wr(p,C3_P_ARM,0);p->gpio=0;p->poisoned=1;
}
static int now(void *context,uint32_t *ms) {
    c3_peripheral_t *p=(c3_peripheral_t *)context;int rc;
    if(!p || !ms) return COOP_EINVAL;
    if(!p->bound || p->poisoned) return COOP_ESTATE;
    rc=c3_shared_now_ms(&p->clock,ms);
    if(rc) abort_bus(p);
    return rc;
}
static int command(c3_peripheral_t *p,uint32_t cmd,uint32_t start,uint32_t timeout) {
    uint32_t n,status,ms;int rc;
    rc=wr(p,C3_P_COMMAND,cmd);if(rc) return rc;
    for(n=0;n<p->config.poll_budget;n++) {
        rc=c3_shared_now_ms(&p->clock,&ms);if(rc) return rc;
        if(!coop_age_valid(ms,start,timeout)) return COOP_ETIMEOUT;
        rc=rd(p,C3_P_STATUS,&status);if(rc) return rc;
        if(!(status&0x100u)) return COOP_ENOTSUP;
        if(status&1u) continue;
        if(!(status&2u)) return COOP_EIO;
        if(status&8u) return COOP_ETIMEOUT;
        if(status&0x30u) return COOP_EIO;
        if(status&4u) return COOP_ENACK;
        return COOP_OK;
    }
    return COOP_ETIMEOUT;
}
static int overlap(const void *a,uint32_t na,const void *b,uint32_t nb) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    if(x>UINTPTR_MAX-na || y>UINTPTR_MAX-nb) return 1;
    return x<y+nb && y<x+na;
}
static int transfer(void *context,uint32_t bus,uint8_t address,const uint8_t *tx,uint32_t nt,
                     uint8_t *rx,uint32_t nr,uint32_t timeout) {
    c3_peripheral_t *p=(c3_peripheral_t *)context;
    uint32_t start,n,value,status;int rc;
    if(!p || bus!=C3_I2C_SENSOR_BUS || address<8 || address>0x77 || (!nt&&!nr) ||
       (nt&&!tx) || (nr&&!rx) || !timeout || timeout>=0x80000000u || nt>4096 || nr>p->scratch_bytes)
        return COOP_EINVAL;
    if((nt && overlap(tx,nt,p->scratch,p->scratch_bytes)) ||
       (nr && overlap(rx,nr,p->scratch,p->scratch_bytes))) return COOP_EINVAL;
    rc=now(p,&start);if(rc) return rc;
    rc=rd(p,C3_P_STATUS,&status);if(rc) goto fail;
    if(status&1u) return COOP_EBUSY;
    if(nt) {
        rc=wr(p,C3_P_TX,(uint32_t)address<<1);if(rc) goto fail;
        rc=command(p,9,start,timeout);if(rc) goto fail;
        for(n=0;n<nt;n++) {
            rc=wr(p,C3_P_TX,tx[n]);if(rc) goto fail;
            rc=command(p,8,start,timeout);if(rc) goto fail;
        }
    }
    if(nr) {
        rc=wr(p,C3_P_TX,((uint32_t)address<<1)|1u);if(rc) goto fail;
        rc=command(p,9,start,timeout);if(rc) goto fail;
        for(n=0;n<nr;n++) {
            rc=command(p,n==nr-1u?20u:4u,start,timeout);if(rc) goto fail;
            rc=rd(p,C3_P_RX,&value);if(rc || value>255u) {if(!rc)rc=COOP_EIO;goto fail;}
            p->scratch[n]=(uint8_t)value;
        }
    }
    rc=command(p,2,start,timeout);if(rc) goto fail;
    rc=rd(p,C3_P_STATUS,&status);if(rc) goto fail;
    if((status&0xc0u)!=0xc0u) {rc=COOP_EIO;goto fail;}
    if(nr) memcpy(rx,p->scratch,nr);
    return COOP_OK;
fail:
    if(rc==COOP_ENACK) {
        int cleanup=rd(p,C3_P_STATUS,&status);
        if(!cleanup && (status&0xc0u)==0xc0u) return rc;
    }
    abort_bus(p);return rc;
}
static int gpio(void *context,uint32_t channel,uint32_t active) {
    c3_peripheral_t *p=(c3_peripheral_t *)context;uint32_t ms,armed,value,new_value;int rc;
    if(!p || channel>1 || active>1) return COOP_EINVAL;
    if(!active && p->poisoned) {rc=wr(p,C3_P_ARM,0);p->gpio=0;return rc?rc:COOP_ESTATE;}
    rc=now(p,&ms);if(rc) return rc;
    rc=rd(p,C3_P_ARM,&armed);if(rc) goto fail;
    if(armed!=1u) {
        p->gpio=0;
        rc=wr(p,C3_P_ARM,0x43474131u);if(rc) goto fail;
    }
    new_value=(p->gpio&~(1u<<channel))|(active<<channel);
    rc=wr(p,C3_P_GPIO,new_value);if(rc) goto fail;
    rc=rd(p,C3_P_GPIO,&value);if(rc) goto fail;
    if(value!=new_value) {rc=COOP_EIO;goto fail;}
    p->gpio=new_value;return COOP_OK;
fail:abort_bus(p);return rc;
}
int c3_peripheral_bind(c3_peripheral_t *p,c3_hal_t *hal,const c2_io_t *io,
                       const c3_peripheral_config_t *cfg,uint8_t *scratch,uint32_t size) {
    uint32_t id,version,hz,enabled,ms,divisor;int rc;
    if(hal) memset(hal,0,sizeof(*hal));
    if(!p) return COOP_EINVAL;
    memset(p,0,sizeof(*p));
    if(!hal || !io || !io->read32 || !io->write32 || !io->barrier || !cfg ||
       !scratch || !size || size>4096 || !cfg->pins_verified) return COOP_ENOTSUP;
    if(cfg->bus_hz<10000 || cfg->bus_hz>1000000 || !cfg->byte_timeout_ms || cfg->byte_timeout_ms>100 ||
       !cfg->poll_budget || !cfg->max_alarm_on_ms || cfg->max_alarm_on_ms>60000 || cfg->active_low_mask>3)
        return COOP_EINVAL;
    p->io=*io;p->config=*cfg;p->scratch=scratch;p->scratch_bytes=size;
    rc=c3_shared_time_bind(&p->clock,io);if(rc) return rc;
    rc=c3_shared_now_ms(&p->clock,&ms);if(rc) return rc;
    if((rc=rd(p,C3_P_ID,&id)) || (rc=rd(p,C3_P_VERSION,&version)) ||
       (rc=rd(p,C3_P_HZ,&hz)) || (rc=rd(p,C3_P_ENABLED,&enabled))) return rc;
    if(id!=0x43335031u || version!=0x00010000u || hz!=100000000u || enabled!=1u) return COOP_ENOTSUP;
    divisor=(hz+cfg->bus_hz*5u-1u)/(cfg->bus_hz*5u);
    if((rc=wr(p,C3_P_ARM,0)) || (rc=wr(p,C3_P_STATUS,1)) ||
       (rc=wr(p,C3_P_DIVISOR,divisor)) || (rc=wr(p,C3_P_TIMEOUT,(hz/1000u)*cfg->byte_timeout_ms)) ||
       (rc=wr(p,C3_P_POLARITY,cfg->active_low_mask)) || (rc=wr(p,C3_P_MAX_ON,cfg->max_alarm_on_ms))) return rc;
    p->bound=1;
    hal->context=p;hal->i2c_write_read=transfer;hal->gpio_write=gpio;hal->checked_now_ms=now;
    return COOP_OK;
}
int c3_peripheral_recover(c3_peripheral_t *p,uint32_t timeout) {
    uint32_t start,status;int rc;
    if(!p || !p->bound || !timeout || timeout>=0x80000000u) return COOP_EINVAL;
    rc=c3_shared_now_ms(&p->clock,&start);if(rc) return rc;
    rc=wr(p,C3_P_COMMAND,64);if(rc) return rc;
    p->gpio=0;p->poisoned=1;
    rc=command(p,32,start,timeout);if(rc) return rc;
    rc=rd(p,C3_P_STATUS,&status);if(rc) return rc;
    if((status&0xfdu)!=0xc0u) return COOP_EIO;
    p->poisoned=0;return COOP_OK;
}
