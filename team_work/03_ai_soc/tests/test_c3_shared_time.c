#include "c3_shared_time.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {uint32_t version,cap,hz,kind,ms,status,reads,status_reads,reset_on_second;int error;} fixture_t;
static fixture_t f;
static int read32(void *context,uint32_t offset,uint32_t *value) {
 fixture_t *p=(fixture_t *)context;++p->reads;
 if(p->error) return p->error;
 switch(offset) {
 case C2_REG_ID:*value=C2_ID;break;
 case C2_REG_VERSION:*value=p->version;break;
 case C2_REG_CAPABILITIES:*value=p->cap;break;
 case C2_REG_TIME_HZ:*value=p->hz;break;
 case C2_REG_TIME_KIND:*value=p->kind;break;
 case C2_REG_TIME_MS:*value=p->ms;break;
 case C2_REG_TIME_STATUS:
  ++p->status_reads;*value=(p->reset_on_second && p->status_reads==2)?0:p->status;break;
 default:return COOP_EIO;
 }return COOP_OK;
}
static void reset(void) {memset(&f,0,sizeof(f));f.version=C2_VERSION;f.cap=7;f.hz=100000000;f.kind=1;f.status=1;}
int main(void) {
 c3_shared_clock_t clock;uint32_t ms=123;unsigned n;
 c2_io_t io={&f,read32,0,0,0,0};
 reset();CHECK(c3_shared_time_bind(&clock,&io)==0);
 for(n=0;n<8;n++) {
  f.ms=0xfffffffcu+n;CHECK(c3_shared_now_ms(&clock,&ms)==0 && ms==f.ms);
 }
 ms=123;f.error=COOP_EIO;CHECK(c3_shared_now_ms(&clock,&ms)==COOP_EIO && ms==123);
 f.error=1;CHECK(c3_shared_now_ms(&clock,&ms)==COOP_EIO && ms==123);
 f.error=0;f.status=0;CHECK(c3_shared_now_ms(&clock,&ms)==COOP_EBUSY && ms==123);
 f.status=1;f.status_reads=0;f.reset_on_second=1;
 CHECK(c3_shared_now_ms(&clock,&ms)==COOP_EBUSY && ms==123);
 reset();f.version=0x00020001u;CHECK(c3_shared_time_bind(&clock,&io)==COOP_ENOTSUP && f.reads==2);
 CHECK(c3_shared_now_ms(&clock,&ms)==COOP_ENOTSUP && ms==123);
 reset();f.cap=3;CHECK(c3_shared_time_bind(&clock,&io)==COOP_ENOTSUP);
 reset();f.hz=50000000;CHECK(c3_shared_time_bind(&clock,&io)==COOP_ENOTSUP);
 reset();f.kind=2;CHECK(c3_shared_time_bind(&clock,&io)==COOP_ENOTSUP);
 reset();CHECK(c3_shared_time_bind(&clock,&io)==0);
 CHECK(c3_shared_time_bind(&clock,0)==COOP_EINVAL);
 CHECK(c3_shared_now_ms(&clock,&ms)==COOP_ENOTSUP);
 CHECK(c3_shared_now_ms(0,&ms)==COOP_EINVAL);
 CHECK(c3_shared_now_ms(&clock,0)==COOP_EINVAL);
 printf("PASS C3 shared time: %u checks; wrap, invalid/reset, IO failure, version/capability/frequency guards; synthetic registers only.\n",checks);
 return 0;
}
