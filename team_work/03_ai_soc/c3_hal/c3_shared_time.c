#include "c3_shared_time.h"
#include <string.h>
static int read_reg(c3_shared_clock_t *clock,uint32_t offset,uint32_t *value) {
    int status=clock->io.read32(clock->io.context,offset,value);
    return status>0?COOP_EIO:status;
}
int c3_shared_time_bind(c3_shared_clock_t *clock,const c2_io_t *io) {
    uint32_t id,version,capabilities,hz,kind;int status;
    if(!clock) return COOP_EINVAL;
    memset(clock,0,sizeof(*clock));
    if(!io || !io->read32) return COOP_EINVAL;
    clock->io=*io;
#define READ(offset,value) do {status=read_reg(clock,offset,&value);if(status)return status;} while(0)
    READ(C2_REG_ID,id);READ(C2_REG_VERSION,version);
    if(id!=C2_ID || version!=C2_VERSION) return COOP_ENOTSUP;
    READ(C2_REG_CAPABILITIES,capabilities);
    if(!(capabilities&C2_CAP_SHARED_TIME)) return COOP_ENOTSUP;
    READ(C2_REG_TIME_HZ,hz);READ(C2_REG_TIME_KIND,kind);
    if(hz!=100000000u || kind!=C2_TIME_KIND_APB_MS) return COOP_ENOTSUP;
#undef READ
    clock->bound=1;return COOP_OK;
}
int c3_shared_now_ms(void *context,uint32_t *ms) {
    c3_shared_clock_t *clock=(c3_shared_clock_t *)context;
    uint32_t before,value,after;int status;
    if(!clock || !ms) return COOP_EINVAL;
    if(!clock->bound) return COOP_ENOTSUP;
    status=read_reg(clock,C2_REG_TIME_STATUS,&before);if(status)return status;
    if(before!=1u) return COOP_EBUSY;
    status=read_reg(clock,C2_REG_TIME_MS,&value);if(status)return status;
    status=read_reg(clock,C2_REG_TIME_STATUS,&after);if(status)return status;
    if(after!=1u) return COOP_EBUSY;
    *ms=value;return COOP_OK;
}
