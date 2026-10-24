#include "cooperation_v1.h"
#include "c3_hal.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
static uint32_t fake_time(void *p) { return *(uint32_t *)p; }
static int fake_i2c(void *p,uint32_t bus,uint8_t address,const uint8_t *tx,
                    uint32_t nt,uint8_t *rx,uint32_t nr,uint32_t timeout) {
    CHECK(bus==0 && address==0x44 && nt==2 && tx[0]==0x24 && timeout==100);
    if (*(uint32_t *)p) return COOP_ETIMEOUT;
    memset(rx,0x5a,nr); return COOP_OK;
}
static int fake_gpio(void *p,uint32_t c,uint32_t a) {
    (void)p; return c==C3_GPIO_ALARM_LED && a==1 ? COOP_OK : COOP_EIO;
}
static coop_frame_t frame(uint32_t id,uint32_t seq) {
    coop_frame_t f={0};
    f.abi_version=COOP_ABI_VERSION; f.frame_id=seq; f.buffer_id=id;
    f.data_offset=id ? COOP_IMAGE1_OFFSET : COOP_IMAGE0_OFFSET;
    f.data_bytes=COOP_IMAGE_BYTES; f.format=COOP_FORMAT_GRAY8;
    f.stride=96; f.valid_flags=COOP_VALID_COMPLETE;
    return f;
}
int main(void) {
    coop_pool_t p; coop_frame_t f,out;
    uint32_t a,ga,b,gb,c,gc,i,t=1234;
    uint8_t rx[6],tx[2]={0x24,0};
    c3_hal_t h={0};
    _Static_assert(sizeof(coop_frame_t)==64,"frame ABI");
    CHECK(coop_fnv1a("hello",5)==0x4f9f2cabu);
    CHECK(coop_age_valid(5,0xfffffff0u,21));
    CHECK(!coop_age_valid(5,0xfffffff0u,20));
    CHECK(!coop_age_valid(100,101,1000));
    CHECK(!coop_age_valid(0x80000000u,0,0x7fffffffu));
    CHECK(!coop_age_valid(1,0,0x80000000u));
    coop_pool_init(&p);
    CHECK(coop_write_begin(&p,&a,&ga)==COOP_OK);
    f=frame(a,1); f.data_bytes=9215;
    CHECK(coop_write_commit(&p,a,ga,&f)==COOP_EINVAL);
    CHECK(coop_read_begin(&p,a,ga,&out)==COOP_ESTATE);
    f=frame(a,1);
    CHECK(coop_write_commit(&p,a,ga,&f)==COOP_OK);
    CHECK(coop_read_begin(&p,a,ga,&out)==COOP_OK && out.frame_id==1);
    CHECK(coop_write_begin(&p,&b,&gb)==COOP_OK && b!=a);
    f=frame(b,2); CHECK(coop_write_commit(&p,b,gb,&f)==COOP_OK);
    CHECK(coop_write_begin(&p,&c,&gc)==COOP_EBUSY && p.dropped_new_frames==1);
    CHECK(p.slots[a].frame.frame_id==1 && p.slots[a].state==COOP_READING);
    CHECK(coop_read_release(&p,a,ga+1)==COOP_ESTATE);
    CHECK(coop_read_release(&p,a,ga)==COOP_OK);
    CHECK(coop_read_release(&p,a,ga)==COOP_ESTATE);
    CHECK(coop_read_begin(&p,b,gb,&out)==COOP_OK);
    CHECK(coop_read_release(&p,b,gb)==COOP_OK);
    /* Exercise reuse and delayed stale commands through many generations. */
    for(i=0;i<2000;++i) {
        uint32_t old_ga=ga;
        CHECK(coop_write_begin(&p,&a,&ga)==COOP_OK);
        CHECK(ga!=old_ga);
        f=frame(a,i); f.valid_flags|=COOP_VALID_MOTION|COOP_VALID_BBOX;
        f.bbox_x0=2; f.bbox_y0=1; f.bbox_x1=95; f.bbox_y1=54;
        CHECK(coop_write_commit(&p,a,ga,&f)==COOP_EINVAL);
        f.bbox_y1=53;
        CHECK(coop_write_commit(&p,a,ga,&f)==COOP_OK);
        CHECK(coop_read_begin(&p,a,old_ga,&out)==COOP_ESTATE);
        CHECK(coop_read_begin(&p,a,ga,&out)==COOP_OK && out.frame_id==i);
        CHECK(coop_write_abort(&p,a,ga)==COOP_ESTATE);
        CHECK(coop_read_release(&p,a,ga)==COOP_OK);
    }
    CHECK(coop_write_begin(&p,&a,&ga)==COOP_OK);
    CHECK(coop_write_abort(&p,a,ga)==COOP_OK);
    CHECK(c3_capabilities(&h)==0);
    CHECK(c3_now_ms(&h,&t)==COOP_ENOTSUP && t==1234);
    memset(rx,0xcc,sizeof(rx));
    CHECK(c3_i2c_write_read(&h,0,0x44,tx,2,rx,6,100)==COOP_ENOTSUP && rx[0]==0xcc);
    CHECK(c3_i2c_write_read(&h,0,0x44,tx,2,rx,6,0)==COOP_EINVAL);
    CHECK(c3_i2c_write_read(&h,0,0x80,tx,2,rx,6,100)==COOP_EINVAL);
    CHECK(c3_gpio_write(&h,0,1)==COOP_ENOTSUP);
    CHECK(c3_gpio_write(&h,2,1)==COOP_EINVAL);
    h.context=&t; h.now_ms=fake_time; h.i2c_write_read=fake_i2c; h.gpio_write=fake_gpio;
    CHECK(c3_capabilities(&h)==7);
    CHECK(c3_now_ms(&h,&i)==COOP_OK && i==1234);
    t=0; CHECK(c3_i2c_write_read(&h,0,0x44,tx,2,rx,6,100)==COOP_OK && rx[5]==0x5a);
    t=1; CHECK(c3_i2c_write_read(&h,0,0x44,tx,2,rx,6,100)==COOP_ETIMEOUT);
    CHECK(c3_gpio_write(&h,0,1)==COOP_OK);
    printf("PASS interface reference tests: %u checks; host simulation only\n",checks);
    return 0;
}

