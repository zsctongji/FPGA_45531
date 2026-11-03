#include <stdint.h>
#include <stddef.h>
#include "bsp.h"
#include "c2_driver.h"
#include "c2_sapphire.h"
#include "build_id.h"

#define C9BASE (IO_APB_SLAVE_0_INPUT+0xe000u)
static c2_io_t io;static c2_sapphire_t platform;static c2_driver_t driver;
static uint8_t image[9216] __attribute__((aligned(64)));
void *memcpy(void *d,const void *s,size_t n){uint8_t *a=d;const uint8_t *b=s;for(size_t i=0;i<n;i++)a[i]=b[i];return d;}
void *memset(void *d,int v,size_t n){uint8_t *a=d;for(size_t i=0;i<n;i++)a[i]=(uint8_t)v;return d;}
static void str(const char *s){while(*s)uart_write(BSP_UART_TERMINAL,*s++);}
static void hex(uint32_t n){for(int i=28;i>=0;i-=4)uart_write(BSP_UART_TERMINAL,"0123456789abcdef"[(n>>i)&15]);}
static void fld(const char *s,uint32_t n){str(s);hex(n);}
static void fence(void){__asm__ volatile("fence iorw,iorw" ::: "memory");}
static uint32_t reg(uint32_t off){fence();uint32_t v=*(volatile uint32_t *)(C9BASE+off);fence();return v;}
static void put(uint32_t off,uint32_t v){fence();*(volatile uint32_t *)(C9BASE+off)=v;fence();}
static int fail(const char *why){str("C9|FAIL stage=");str(why);str("\r\n");return 1;}
void trap_report(uint32_t cause,uint32_t pc,uint32_t val){str("C9|TRAP");fld(" cause=",cause);fld(" pc=",pc);fld(" value=",val);str("\r\n");fail("trap");}
static int snapshot(const char *label){
 const uint32_t bases[]={0x40,0x60,0x80,0xa0,0xc0};
 str("C9|SNAP_BEGIN label=");str(label);fld(" start_ms=",*(volatile uint32_t *)(IO_APB_SLAVE_0_INPUT+C2_REG_TIME_MS));str("\r\n");
 for(unsigned pair=0;pair<4;pair++){
  uint64_t start=clint_getTime(BSP_CLINT);put(0x10,(pair<<8)|1);
  while(!(reg(0x10)&2)){if(clint_getTime(BSP_CLINT)-start>100000000)return fail("snapshot_timeout");}
  for(unsigned b=0;b<5;b++){
   uint32_t low=reg(bases[b]),high=reg(bases[b]+4);
   str("C9|BANK");fld(" pair=",pair);fld(" bank=",b);fld(" sequence=",reg(0x14));fld(" lo=",low);fld(" hi=",high);str("\r\n");
  }
  put(0x14,1);
 }
 str("C9|SNAP_END label=");str(label);fld(" end_ms=",*(volatile uint32_t *)(IO_APB_SLAVE_0_INPUT+C2_REG_TIME_MS));str(" pairs=4\r\n");return 0;
}
static int check_map(void){
 if(reg(0)!=0x43394c34 || reg(4)!=4)return fail("acceptance_id_or_source_active");
 volatile uint32_t *locations[]={ (volatile uint32_t *)0x07010000,(volatile uint32_t *)0x08010000,(volatile uint32_t *)0x0820b000,(volatile uint32_t *)0x08406000,(volatile uint32_t *)0x09011000,(volatile uint32_t *)0x09014000};
 for(unsigned n=0;n<6;n++)for(unsigned w=0;w<4;w++)locations[n][w]=0xc9a70000u+(n<<8)+w;
 __asm__ volatile("fence iorw,iorw\n.word 0x500f\nfence iorw,iorw" ::: "memory");
 for(unsigned n=0;n<6;n++)for(unsigned w=0;w<4;w++)if(locations[n][w]!=(0xc9a70000u+(n<<8)+w))return fail("candidate_address_alias");
 str("C9|MAP status=PASS independent_locations=6 words=24 source_off=1\r\n");return 0;
}
static int kick(uint8_t gray){uint64_t start=clint_getTime(BSP_CLINT);while(!reg(8)){if(clint_getTime(BSP_CLINT)-start>100000000)return fail("pattern_command_timeout");}put(8,gray);return 0;}
static int take(uint32_t slot,c2_reply_t *out){
 c2_reply_t q;uint64_t start=clint_getTime(BSP_CLINT);
 for(;;){
  int s=c2_exchange(&driver,C2_CMD_QUERY,slot,0,&q);if(s)return fail("query");
  if(q.protocol_error)return fail("axi_protocol");
  if(((q.states>>(2*slot))&3)==COOP_READY)break;
  if(clint_getTime(BSP_CLINT)-start>200000000)return fail("frame_timeout");
 }
 if(c2_exchange(&driver,C2_CMD_ACQUIRE,slot,q.generation,out))return fail("acquire");
 if(out->frame.data_bytes!=9216 || out->frame.buffer_id!=slot || out->frame.data_offset!=(slot?0x4000u:0x1000u))return fail("descriptor");
 return 0;
}
static int release(uint32_t slot,uint32_t generation){c2_reply_t r;if(c2_exchange(&driver,C2_CMD_RELEASE,slot,generation,&r))return fail("release");return 0;}
static int copy_check(c2_reply_t *a,uint8_t expected){
 if(io.sync_for_cpu(io.context,a->frame.data_offset,9216) || io.copy_from_dma(io.context,a->frame.data_offset,image,9216))return fail("invalidate_copy");
 for(unsigned n=0;n<9216;n++){uint8_t want=n<2016 || n>=7200?0:expected;if(image[n]!=want)return fail("pixel_pattern");}
 if(coop_fnv1a(image,9216)!=a->frame.checksum_fnv1a)return fail("dma_fnv");
 str("C9|FRAME status=PASS");fld(" frame=",a->frame.frame_id);fld(" generation=",a->generation);fld(" raw_fnv=",a->frame.checksum_fnv1a);fld(" seed=",expected);str("\r\n");return 0;
}
int main(void){
 bsp_init();str("C9|BOOT mode=coherence version=" C9_DMA_BUILD_ID "\r\n");
 if(check_map())return 1;
 if(c2_sapphire_bind(&io,&platform,IO_APB_SLAVE_0_INPUT,0x09010000,1) || c2_driver_init(&driver,&io,100000))return fail("driver_bind");
 if(snapshot("before"))return 1;
 put(4,0xc9a70003);if(reg(4)!=7)return fail("source_commit");
 if(kick(0x3c))return 1;c2_reply_t first,second,third,answer;
 if(take(0,&first))return 1;
 if(io.sync_for_cpu(io.context,first.frame.data_offset,9216))return fail("prime_invalidate");
 volatile const uint32_t *line=(volatile const uint32_t *)(0x09010000+first.frame.data_offset+2048);
 // Keep this critical interval free of UART/large copies so the probe cache
 // line remains resident while an independent C2 AXI master updates DDR.
 for(unsigned n=0;n<16;n++)if(line[n]!=0x3c3c3c3c)return fail("cache_prime");
 if(release(0,first.generation) || kick(0xc3) || take(0,&second))return 1;
 unsigned stale=0;for(unsigned n=0;n<16;n++)if(line[n]==0x3c3c3c3c)stale++;
 if(stale!=16)return fail("negative_stale_not_observed");
 if(io.sync_for_cpu(io.context,second.frame.data_offset,9216))return fail("fresh_invalidate");
 unsigned fresh=0;for(unsigned n=0;n<16;n++)if(line[n]==0xc3c3c3c3)fresh++;
 str("C9|CACHE_NEGATIVE");fld(" stale_words=",stale);str(" omit_invalidate=OLD_DATA\r\n");
 str("C9|CACHE_POSITIVE");fld(" fresh_words=",fresh);str(" invalidate=FRESH_DATA\r\n");
 if(fresh!=16 || second.generation<=first.generation || copy_check(&second,0xc3))return fail("fresh_data");
 if(c2_exchange(&driver,C2_CMD_RELEASE,0,first.generation,&answer)!=COOP_ESTATE || ((answer.states&3)!=COOP_READING))return fail("stale_release_token");
 if(kick(0x5a) || take(1,&third))return 1;
 if(io.sync_for_cpu(io.context,second.frame.data_offset,9216))return fail("ownership_invalidate");
 for(unsigned n=0;n<16;n++)if(line[n]!=0xc3c3c3c3)return fail("leased_slot_overwritten");
 if(copy_check(&third,0x5a) || release(1,third.generation) || release(0,second.generation))return 1;
 str("C9|OWNERSHIP status=PASS stale_token_rejected=1 leased_slot_preserved=1 other_slot=1\r\n");
 uint64_t start=clint_getTime(BSP_CLINT);while(clint_getTime(BSP_CLINT)-start<20000000){}
 if(snapshot("after"))return 1;
 str("C9|DONE status=PASS mode=coherence version=" C9_DMA_BUILD_ID "\r\n");return 0;
}
