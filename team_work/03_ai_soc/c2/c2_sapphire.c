#include "c2_sapphire.h"
#include "soc.h"
#if !defined(__riscv) || __riscv_xlen != 32
#error "This backend requires the pinned RV32 Sapphire/VexRiscv core"
#endif
#if SYSTEM_CORES_0_BYTES_PER_LINE != 64
#error "Re-audit cache-line ownership/alignment for this core"
#endif
static void barrier(void *context) {
    (void)context;__asm__ volatile("fence iorw, iorw" ::: "memory");
}
static int read32(void *context,uint32_t offset,uint32_t *value) {
    c2_sapphire_t *s=(c2_sapphire_t *)context;
    if((offset&3u) || offset>=0x10000u || !value) return COOP_EINVAL;
    barrier(context);*value=*(volatile const uint32_t *)(s->apb_base+offset);barrier(context);
    if(offset==C2_REG_SHARED_BASE && *value!=s->shared_base) return COOP_EIO;
    return COOP_OK;
}
static int write32(void *context,uint32_t offset,uint32_t value) {
    c2_sapphire_t *s=(c2_sapphire_t *)context;
    if((offset&3u) || offset>=0x10000u) return COOP_EINVAL;
    barrier(context);*(volatile uint32_t *)(s->apb_base+offset)=value;barrier(context);return COOP_OK;
}
static int sync_for_cpu(void *context,uint32_t offset,uint32_t bytes) {
    (void)context;
    if((offset!=COOP_IMAGE0_OFFSET && offset!=COOP_IMAGE1_OFFSET) || bytes!=COOP_IMAGE_BYTES) return COOP_EINVAL;
    /* Vendor vexriscv.h and generated CPU decode identify this instruction as
       whole D-cache invalidation. It is NOT fence.i or a generic RISC-V CMO.
       Volatile + memory clobber prevents C compiler reordering across it. */
    __asm__ volatile("fence iorw, iorw\n.word 0x0000500f\nfence iorw, iorw" ::: "memory");
    return COOP_OK;
}
static int copy_from_dma(void *context,uint32_t offset,uint8_t *destination,uint32_t bytes) {
    c2_sapphire_t *s=(c2_sapphire_t *)context;uint32_t n;
    volatile const uint8_t *source;
    if(!destination || bytes!=COOP_IMAGE_BYTES || (offset!=COOP_IMAGE0_OFFSET && offset!=COOP_IMAGE1_OFFSET)) return COOP_EINVAL;
    if((uintptr_t)destination>UINTPTR_MAX-bytes) return COOP_EINVAL;
    if((uintptr_t)destination<s->shared_base+COOP_SHARED_BYTES &&
       (uintptr_t)destination+bytes>s->shared_base) return COOP_EINVAL;
    source=(volatile const uint8_t *)(s->shared_base+offset);
    for(n=0;n<bytes;n++) destination[n]=source[n];
    return COOP_OK;
}
int c2_sapphire_bind(c2_io_t *io,c2_sapphire_t *s,uintptr_t apb,uintptr_t shared,int verified) {
    if(!io || !s || !verified) return COOP_ENOTSUP;
    if(apb!=IO_APB_SLAVE_0_INPUT || (shared&0xffffu) ||
       shared>UINTPTR_MAX-COOP_SHARED_BYTES) return COOP_EINVAL;
    s->apb_base=apb;s->shared_base=shared;
    io->context=s;io->read32=read32;io->write32=write32;
    io->sync_for_cpu=sync_for_cpu;io->copy_from_dma=copy_from_dma;io->barrier=barrier;
    return COOP_OK;
}
