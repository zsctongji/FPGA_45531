#include "c3_sapphire_peripheral.h"
#include "soc.h"
#if !defined(__riscv) || __riscv_xlen!=32
#error "RV32 Sapphire backend only"
#endif
static void barrier(void *context) {(void)context;__asm__ volatile("fence iorw, iorw" ::: "memory");}
static int read32(void *context,uint32_t offset,uint32_t *value) {
    c3_sapphire_io_t *s=(c3_sapphire_io_t *)context;
    if(!value || (offset&3u) || offset>=IO_APB_SLAVE_0_INPUT_SIZE) return COOP_EINVAL;
    barrier(context);*value=*(volatile const uint32_t *)(s->apb_base+offset);barrier(context);
    return COOP_OK;
}
static int write32(void *context,uint32_t offset,uint32_t value) {
    c3_sapphire_io_t *s=(c3_sapphire_io_t *)context;
    if((offset&3u) || offset>=IO_APB_SLAVE_0_INPUT_SIZE) return COOP_EINVAL;
    barrier(context);*(volatile uint32_t *)(s->apb_base+offset)=value;barrier(context);return COOP_OK;
}
int c3_sapphire_peripheral_bind(c3_peripheral_t *p,c3_hal_t *hal,c3_sapphire_io_t *s,
                                const c3_peripheral_config_t *cfg,uint8_t *scratch,uint32_t n,int verified) {
    c2_io_t io={0};
    if(!verified || !s) return COOP_ENOTSUP;
    s->apb_base=IO_APB_SLAVE_0_INPUT;
    io.context=s;io.read32=read32;io.write32=write32;io.barrier=barrier;
    return c3_peripheral_bind(p,hal,&io,cfg,scratch,n);
}
