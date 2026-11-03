#include <stdint.h>
#include "bsp.h"
#include "c2_driver.h"
#include "build_id.h"
#define C9BASE (IO_APB_SLAVE_0_INPUT+0xe000u)
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

int main(void){
 bsp_init();str("C9|BOOT mode=geometry version=" C9_GEOMETRY_BUILD_ID "\r\n");
 if(check_map() || snapshot("before"))return 1;
 put(4,0xc9a70001);if(reg(4)!=5)return fail("source_commit");
 str("C9|GEOMETRY protocol=1 synthetic=0 upper_flags=width12_height12_seen_complete_clip2\r\n");
 uint64_t start=clint_getTime(BSP_CLINT);
 while(clint_getTime(BSP_CLINT)-start<1000000000ULL){}
 if(snapshot("after"))return 1;
 str("C9|DONE mode=geometry version=" C9_GEOMETRY_BUILD_ID "\r\n");return 0;
}
