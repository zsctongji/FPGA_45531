/* Standalone CPU-side C7 diagnostic. Destructive only in the ranges below.
 * External DMA cache-coherence testing is a separate acceptance item. */
#include <stdint.h>
#include "bsp.h"
#include "c2_driver.h"
#include "build_id.h"

#if SYSTEM_CORES_0_DCACHE_SIZE != 4096 || SYSTEM_CORES_0_BYTES_PER_LINE != 64
#error Re-audit this diagnostic for the changed CPU cache
#endif
static void str(const char *s) { while (*s) uart_write(BSP_UART_TERMINAL, *s++); }
static void hex(uint32_t n) { for(int i=28;i>=0;i-=4) uart_write(BSP_UART_TERMINAL,"0123456789abcdef"[(n>>i)&15]); }
static void field(const char *name,uint32_t n) {str(name);hex(n);}
static void invalidate(void) { __asm__ volatile("fence iorw,iorw\n.word 0x0000500f\nfence iorw,iorw" ::: "memory"); }
static uint32_t reg32(uint32_t off) {return *(volatile uint32_t *)(IO_APB_SLAVE_0_INPUT+off);}
static int fail(const char *why) {str("C7|FAIL stage=");str(why);str("\r\n");return 1;}
void trap_report(uint32_t cause,uint32_t pc,uint32_t value) {
 str("C7|TRAP");field(" cause=",cause);field(" pc=",pc);field(" value=",value);str("\r\n");fail("trap");
}
static int mismatch(uint32_t a,uint32_t want,uint32_t got) {
 str("C7|MISMATCH");field(" address=",a);field(" expected=",want);field(" actual=",got);str("\r\n");return fail("memory");
}
static uint32_t pattern(uint32_t a,unsigned p) {
 if(p==0)return 0;
 if(p==1)return 0xffffffff;
 if(p==2)return a^0x5aa55aa5;
 a^=0x9e3779b9;a^=a<<13;a^=a>>17;a^=a<<5;return a;
}
int main(void) {
 static const uint32_t bases[]={0x02000000,0x04000000,0x06000000,0x07000000};
 const unsigned words=65536;
 bsp_init();str("C7|BOOT version=" C7_DIAG_BUILD_ID " cpu_hz=100000000 clint_hz=100000000\r\n");
 uint32_t id=reg32(C2_REG_ID),version=reg32(C2_REG_VERSION),map=reg32(C2_REG_MAP_ENABLED);
 str("C7|APB");field(" id=",id);field(" version=",version);field(" map=",map);
 field(" shared=",reg32(C2_REG_SHARED_BASE));field(" errors=",reg32(C2_REG_PROTOCOL_ERROR));str("\r\n");
 if(id!=C2_ID || version!=C2_VERSION || map!=0 || reg32(C2_REG_PROTOCOL_ERROR)!=0)return fail("apb_contract");
 uint32_t time_hz=reg32(C2_REG_TIME_HZ),kind=reg32(C2_REG_TIME_KIND),valid=reg32(C2_REG_TIME_STATUS);
 if(time_hz!=100000000 || kind!=1 || !(valid&1))return fail("time_contract");
 uint32_t ms0=reg32(C2_REG_TIME_MS);uint64_t ticks0=clint_getTime(BSP_CLINT);
 while(clint_getTime(BSP_CLINT)-ticks0<10000000){}
 uint64_t ticks1=clint_getTime(BSP_CLINT);uint32_t ms1=reg32(C2_REG_TIME_MS);
 str("C7|TIME");field(" ticks_hi=",(uint32_t)((ticks1-ticks0)>>32));field(" ticks_lo=",(uint32_t)(ticks1-ticks0));field(" ms_delta=",ms1-ms0);str("\r\n");
 if(ms1-ms0<99 || ms1-ms0>102)return fail("time_delta");
 uint32_t checked=0;
 for(unsigned p=0;p<4;p++) {
  for(unsigned b=0;b<4;b++) {
   volatile uint32_t *mem=(volatile uint32_t *)bases[b];
   for(unsigned i=0;i<words;i++)mem[i]=pattern(bases[b]+4*i,p);
  }
  invalidate();
  for(unsigned b=0;b<4;b++) {
   volatile uint32_t *mem=(volatile uint32_t *)bases[b];
   for(unsigned i=0;i<words;i++) {
    uint32_t want=pattern(bases[b]+4*i,p),got=mem[i];
    if(got!=want)return mismatch(bases[b]+4*i,want,got);
    checked++;
   }
  }
  str("C7|MEMORY_PASS");field(" pattern=",p);field(" checked=",checked);str("\r\n");
 }
 volatile uint8_t *bytes=(volatile uint8_t *)bases[0];
 for(unsigned i=0;i<256;i++)bytes[i]=(uint8_t)i;
 invalidate();
 for(unsigned i=0;i<64;i++) {
  uint32_t want=(4*i)|((4*i+1)<<8)|((4*i+2)<<16)|((4*i+3)<<24);
  uint32_t got=((volatile uint32_t *)bytes)[i];if(got!=want)return mismatch(bases[0]+4*i,want,got);
 }
 volatile uint16_t *halves=(volatile uint16_t *)bases[0];
 for(unsigned i=0;i<128;i++)halves[i]=(uint16_t)(0x1234+3*i);
 invalidate();
 for(unsigned i=0;i<64;i++) {
  uint32_t want=(0x1234+6*i)|((0x1237+6*i)<<16),got=((volatile uint32_t *)bytes)[i];
  if(got!=want)return mismatch(bases[0]+4*i,want,got);
 }
 str("C7|LANES byte=PASS halfword=PASS cross16=PASS cross64=PASS\r\n");
 str("C7|CACHE opcode=0000500f line_bytes=64 cache_bytes=4096 invalidate_refill=PASS dma_coherence=UNTESTED\r\n");
 if(reg32(C2_REG_PROTOCOL_ERROR)!=0)return fail("axi_protocol_error");
 str("C7|DONE status=PASS");field(" checked=",checked);str(" version=" C7_DIAG_BUILD_ID "\r\n");
 return 0;
}
