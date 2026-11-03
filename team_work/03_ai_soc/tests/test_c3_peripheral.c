#include "c3_peripheral.h"
#include "c3_thermal_publish.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{checks++;if(!(x)){printf("FAIL line %d: %s\n",__LINE__,#x);return 1;}}while(0)
typedef struct {
 uint32_t regs[64],ms,commands[64],tx[64],nc,nt,rx_index,busy_reads,nack_at,
          timeout_at,arbitration_at,clock_error,clock_stopped,broken_clock,write_error,bad_rx,
          enabled,stuck,never_done;
} fixture_t;
static int checks=0;
static fixture_t f;
static void barrier(void *context){(void)context;}
static int read32(void *context,uint32_t offset,uint32_t *v) {
 fixture_t *s=(fixture_t *)context;uint32_t reg=offset-C3_PAGE;
 if(offset<C3_PAGE) {
  switch(offset) {
   case C2_REG_ID:*v=C2_ID;break;case C2_REG_VERSION:*v=C2_VERSION;break;
   case C2_REG_CAPABILITIES:*v=7;break;case C2_REG_TIME_HZ:*v=100000000;break;
   case C2_REG_TIME_KIND:*v=1;break;
   case C2_REG_TIME_STATUS:*v=s->clock_stopped?0u:1u;break;
   case C2_REG_TIME_MS:if(s->clock_error)return COOP_EIO;*v=s->broken_clock?s->ms-10:s->ms;break;
   default:return COOP_EINVAL;
  }return 0;
 }
 switch(reg) {
  case C3_P_ID:*v=0x43335031u;break;case C3_P_VERSION:*v=0x10000u;break;
  case C3_P_HZ:*v=100000000;break;case C3_P_ENABLED:*v=s->enabled;break;
  case C3_P_STATUS:
   *v=(s->enabled?0x100u:0u)|0xc2u;
   if(s->busy_reads || (s->never_done && s->nc)) {if(s->busy_reads)s->busy_reads--;*v=0x101u;}
   else if(s->nc && s->commands[s->nc-1]!=32 && s->commands[s->nc-1]!=64) {
    if(s->nc==s->nack_at)*v|=4;
    if(s->nc==s->timeout_at)*v|=8;
    if(s->nc==s->arbitration_at)*v|=16;
   }
   if(s->stuck)*v&=~0xc0u;
   break;
  case C3_P_RX:*v=s->bad_rx?256u:0x12u+s->rx_index++;break;
  default:if(reg>=256)return COOP_EINVAL;*v=s->regs[reg/4];break;
 }return 0;
}
static int write32(void *context,uint32_t offset,uint32_t v) {
 fixture_t *s=(fixture_t *)context;uint32_t reg=offset-C3_PAGE;
 if(offset==s->write_error)return COOP_EIO;
 if(reg>=256)return COOP_EINVAL;
 if(reg==C3_P_COMMAND) {
  if(s->nc>=64)return COOP_EIO;
  s->commands[s->nc++]=v;s->busy_reads=1;
  if(v==64){s->regs[C3_P_ARM/4]=0;s->regs[C3_P_GPIO/4]=0;s->busy_reads=0;}
 } else if(reg==C3_P_TX) s->tx[s->nt++]=v;
 else if(reg==C3_P_ARM){s->regs[reg/4]=v==0x43474131u;s->regs[C3_P_GPIO/4]=0;}
 else s->regs[reg/4]=v;
 return 0;
}
static void reset(void){memset(&f,0,sizeof(f));f.enabled=1;f.ms=0xfffffff0u;}
static int bind(c3_peripheral_t *p,c3_hal_t *h,uint8_t *scratch) {
 c2_io_t io={&f,read32,write32,0,0,barrier};
 c3_peripheral_config_t c={400000,20,100,3000,0,1};
 return c3_peripheral_bind(p,h,&io,&c,scratch,64);
}
int main(void) {
 c3_peripheral_t p;c3_hal_t h;uint8_t scratch[64],tx[2]={0,0x80},rx[2]={0xa5,0xa5};
 uint32_t now=123,n;
 coop_thermal_t input,out,sentinel;c3_thermal_quality_t q={99,99,99},savedq=q;
 reset();CHECK(bind(&p,&h,scratch)==0);CHECK(c3_capabilities(&h)==15);
 CHECK(h.now_ms==0 && h.checked_now_ms!=0);
 CHECK(c3_now_ms(&h,&now)==0 && now==0xfffffff0u);
 CHECK(c3_i2c_write_read(&h,0,0x33,tx,2,rx,2,100)==0);
 CHECK(rx[0]==0x12 && rx[1]==0x13 && f.nc==7);
 CHECK(f.commands[0]==9 && f.commands[1]==8 && f.commands[2]==8 &&
       f.commands[3]==9 && f.commands[4]==4 && f.commands[5]==20 && f.commands[6]==2);
 CHECK(f.nt==4 && f.tx[0]==0x66 && f.tx[1]==0 && f.tx[2]==0x80 && f.tx[3]==0x67);
 CHECK(f.regs[C3_P_DIVISOR/4]==50 && f.regs[C3_P_TIMEOUT/4]==2000000);
 CHECK(c3_gpio_write(&h,1,1)==0 && f.regs[C3_P_GPIO/4]==2);
 CHECK(c3_gpio_write(&h,0,1)==0 && f.regs[C3_P_GPIO/4]==3);
 CHECK(c3_gpio_write(&h,1,0)==0 && f.regs[C3_P_GPIO/4]==1);
 f.regs[C3_P_ARM/4]=0;f.regs[C3_P_GPIO/4]=0;
 CHECK(c3_gpio_write(&h,0,1)==0 && f.regs[C3_P_GPIO/4]==1);
 reset();CHECK(bind(&p,&h,scratch)==0);f.nack_at=1;
 CHECK(c3_i2c_write_read(&h,0,0x33,tx,2,rx,2,100)==COOP_ENACK && !p.poisoned);
 reset();CHECK(bind(&p,&h,scratch)==0);f.timeout_at=4;rx[0]=0xa5;rx[1]=0xa5;
 CHECK(c3_i2c_write_read(&h,0,0x33,tx,2,rx,2,100)==COOP_ETIMEOUT && p.poisoned);
 CHECK(rx[0]==0xa5 && rx[1]==0xa5 && f.commands[f.nc-1]==64);
 CHECK(c3_gpio_write(&h,1,1)==COOP_ESTATE);
 CHECK(c3_peripheral_recover(&p,20)==0 && !p.poisoned && !p.gpio);
 reset();CHECK(bind(&p,&h,scratch)==0);f.arbitration_at=2;
 CHECK(c3_i2c_write_read(&h,0,0x33,tx,2,0,0,100)==COOP_EIO && p.poisoned);
 reset();CHECK(bind(&p,&h,scratch)==0);f.never_done=1;
 CHECK(c3_i2c_write_read(&h,0,0x33,tx,2,0,0,100)==COOP_ETIMEOUT && p.poisoned);
 reset();CHECK(bind(&p,&h,scratch)==0);f.clock_error=1;now=123;
 CHECK(c3_now_ms(&h,&now)==COOP_EIO && now==123 && p.poisoned);
 CHECK(!f.regs[C3_P_ARM/4]);
 reset();CHECK(bind(&p,&h,scratch)==0);f.clock_stopped=1;now=123;
 CHECK(c3_now_ms(&h,&now)==COOP_EBUSY && now==123 && p.poisoned);
 reset();CHECK(bind(&p,&h,scratch)==0);f.bad_rx=1;rx[0]=0xa5;
 CHECK(c3_i2c_write_read(&h,0,0x33,0,0,rx,1,100)==COOP_EIO && rx[0]==0xa5);
 reset();CHECK(bind(&p,&h,scratch)==0);
 CHECK(c3_i2c_write_read(&h,1,0x33,tx,2,rx,2,100)==COOP_EINVAL);
 CHECK(c3_i2c_write_read(&h,0,0x33,tx,2,scratch,2,100)==COOP_EINVAL);
 f.write_error=C3_PAGE+C3_P_GPIO;
 CHECK(c3_gpio_write(&h,1,1)==COOP_EIO && p.poisoned && !f.regs[C3_P_ARM/4]);
 reset();f.enabled=0;CHECK(bind(&p,&h,scratch)==COOP_ENOTSUP && !c3_capabilities(&h));
 reset();CHECK(bind(&p,&h,scratch)==0);
 memset(&input,0,sizeof(input));input.abi_version=COOP_ABI_VERSION;input.timestamp_ms=f.ms-400u;
 input.valid_flags=3;input.error_bits=64;
 memset(input.pixel_valid_bits,255,96);input.pixel_valid_bits[620/8]&=(uint8_t)(255u^(1u<<(620%8)));
 for(n=0;n<768;n++)if(n!=620)input.temperature_centi_c[n]=2500;
 memset(&out,0xa5,sizeof(out));sentinel=out;
 CHECK(c3_publish_thermal(&h,&input,C3_THERMAL_STRICT,&out,&q)==COOP_ESTATE);
 CHECK(!memcmp(&out,&sentinel,sizeof(out)) && !memcmp(&q,&savedq,sizeof(q)));
 CHECK(c3_publish_thermal(&h,&input,C3_THERMAL_ALLOW_BAD_620,&out,&q)==0);
 CHECK(q.valid_pixels==767 && q.quality==C3_THERMAL_QUALITY_MASKED && q.age_ms==400 && !memcmp(&input,&out,sizeof(input)));
 input.timestamp_ms=f.ms-500u;CHECK(c3_publish_thermal(&h,&input,1,&out,&q)==0);
 input.timestamp_ms=f.ms-501u;CHECK(c3_publish_thermal(&h,&input,1,&out,&q)==COOP_ETIMEOUT);
 input.timestamp_ms=f.ms+1u;CHECK(c3_publish_thermal(&h,&input,1,&out,&q)==COOP_ETIMEOUT);
 input.timestamp_ms=f.ms-1u;input.pixel_valid_bits[0]&=0xfe;CHECK(c3_publish_thermal(&h,&input,1,&out,&q)==COOP_ESTATE);
 input.pixel_valid_bits[0]=255;input.valid_flags=7;CHECK(c3_publish_thermal(&h,&input,1,&out,&q)==COOP_ESTATE);
 input.error_bits=0;input.pixel_valid_bits[620/8]=255;
 CHECK(c3_publish_thermal(&h,&input,0,&out,&q)==0 && q.quality==C3_THERMAL_QUALITY_FULL && q.valid_pixels==768);
 f.clock_error=1;CHECK(c3_publish_thermal(&h,&input,0,&out,&q)==COOP_EIO);
 CHECK(p.poisoned);
 printf("PASS C3 peripheral host checks=%d checked_time byte_commands repeated_START staged_RX failure_cleanup watchdog_rearm thermal_mask_policy deadlines\n",checks);
 return 0;
}
