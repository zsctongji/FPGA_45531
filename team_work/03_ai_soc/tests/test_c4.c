#include "c4_bridge.h"
#include "c3_replay.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,calls;
#define CHECK(x) do { ++checks; if(!(x)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x); exit(1); } } while(0)
static uint8_t shared[COOP_SHARED_BYTES],small[96*54],gray[9216];
static int8_t tensor[9216];
static coop_pool_t pool;
static c4_consumer_t consumer;
static uint32_t id,generation;
static int fail_infer;
static int infer(void *ctx,const int8_t *t,uint32_t n,int8_t out[2]) {
    uint32_t i; (void)ctx;
    ++calls; CHECK(n==9216);
    for(i=0;i<n;++i) CHECK((int)t[i]==(int)shared[(id?COOP_IMAGE1_OFFSET:COOP_IMAGE0_OFFSET)+i]-128);
    if(fail_infer) return COOP_EIO;
    out[0]=-70; out[1]=70; return COOP_OK;
}
static void publish(uint32_t seq,uint32_t timestamp) {
    coop_frame_t f={0}; uint32_t i;
    CHECK(coop_write_begin(&pool,&id,&generation)==COOP_OK);
    f.abi_version=COOP_ABI_VERSION; f.frame_id=seq; f.timestamp_ms=timestamp; f.buffer_id=id;
    f.data_offset=id?COOP_IMAGE1_OFFSET:COOP_IMAGE0_OFFSET;
    f.data_bytes=9216; f.format=COOP_FORMAT_GRAY8; f.stride=96; f.valid_flags=COOP_VALID_COMPLETE;
    for(i=0;i<9216;++i) shared[f.data_offset+i]=(uint8_t)(i*17u+seq);
    f.checksum_fnv1a=coop_fnv1a(shared+f.data_offset,9216);
    CHECK(coop_write_commit(&pool,id,generation,&f)==COOP_OK);
}
static int process(uint32_t now,c4_result_t *r) {
    return c4_process(&consumer,&pool,id,generation,shared,sizeof(shared),now,
                      tensor,sizeof(tensor),infer,0,r);
}
int main(void) {
    uint32_t i,j,old_calls;
    c4_result_t r; c3_hal_t h; c3_replay_t replay={0};
    uint8_t cmd[2]={0x24,0},reply[3]={1,2,3},rx[3]={0};
    c3_replay_step_t steps[]={
        {0x44,cmd,reply,2,3,5,COOP_OK},
        {0x44,cmd,reply,2,3,200,COOP_OK},
        {0x44,cmd,reply,2,3,1,COOP_ENACK}
    };
    for(i=0;i<sizeof(small);++i) small[i]=(uint8_t)i;
    CHECK(c4_pad_gray54(small,sizeof(small),gray,sizeof(gray))==COOP_OK);
    for(i=0;i<96*96;++i) CHECK(gray[i]==(i<21*96||i>=75*96 ? 0 : small[i-21*96]));
    CHECK(c4_pad_gray54(small,1,gray,sizeof(gray))==COOP_EINVAL);
    CHECK(c4_gray_to_vendor_int8(gray,9216,tensor,9216)==COOP_OK);
    for(i=0;i<9216;++i) CHECK((int)tensor[i]==(int)gray[i]-128);
    CHECK(c4_gray_to_vendor_int8(gray,9215,tensor,9216)==COOP_EINVAL);
    CHECK(c4_gray_to_vendor_int8(gray,9216,(int8_t *)gray+1,9216)==COOP_EINVAL);
    coop_pool_init(&pool); memset(&consumer,0,sizeof(consumer));
    for(i=0;i<128;++i) {
        publish(i,1000+i);
        CHECK(process(1000+i,&r)==COOP_OK && r.valid && r.predicted==1 && r.frame_id==i);
        CHECK(pool.slots[id].state==COOP_FREE);
    }
    old_calls=calls;
    publish(128,2000); shared[pool.slots[id].frame.data_offset]^=1;
    CHECK(process(2000,&r)==C4_ECHECKSUM && !r.valid);
    CHECK(calls==old_calls && pool.slots[id].state==COOP_FREE);
    publish(128,2000); CHECK(process(3001,&r)==C4_ESTALE && !r.valid);
    publish(128,2001); CHECK(process(2000,&r)==C4_ESTALE && !r.valid);
    publish(127,2000); CHECK(process(2000,&r)==C4_EORDER && !r.valid);
    publish(126,2000); CHECK(process(2000,&r)==C4_EORDER && !r.valid);
    publish(128,2000); fail_infer=1; CHECK(process(2000,&r)==COOP_EIO && !r.valid);
    CHECK(pool.slots[id].state==COOP_FREE && consumer.last_frame_id==127);
    fail_infer=0;
    publish(128,2000);
    CHECK(c4_process(&consumer,&pool,id,generation,shared,32,2000,tensor,sizeof(tensor),infer,0,&r)==COOP_EINVAL);
    CHECK(pool.slots[id].state==COOP_FREE);
    publish(128,2000);
    CHECK(c4_process(&consumer,&pool,id,generation,shared,sizeof(shared),2000,
                    (int8_t *)shared,9216,infer,0,&r)==COOP_EINVAL);
    publish(128,2000);
    CHECK(c4_process(&consumer,&pool,id,generation,shared,sizeof(shared),2000,tensor,9216,0,0,&r)==COOP_ENOTSUP);
    CHECK(pool.slots[id].state==COOP_FREE);
    publish(128,2000); CHECK(process(3000,&r)==COOP_OK); /* exact age boundary */
    memset(&consumer,0,sizeof(consumer));
    publish(0xffffffffu,0xfffffff0u); CHECK(process(5,&r)==COOP_OK);
    publish(0,6); CHECK(process(6,&r)==COOP_OK);
    /* Busy producer cannot overwrite READING/READY slots. */
    publish(1,7); CHECK(coop_read_begin(&pool,id,generation,&pool.slots[id].frame)==COOP_OK);
    publish(2,8);
    CHECK(coop_write_begin(&pool,&i,&j)==COOP_EBUSY && pool.dropped_new_frames==1);
    coop_pool_init(&pool);
    CHECK(c4_publish_gray_reference(&pool,shared,sizeof(shared),gray,9215,3,9,&id,&generation)==COOP_EINVAL);
    CHECK(c4_publish_gray_reference(&pool,shared,sizeof(shared),gray,9216,3,9,&id,&generation)==COOP_OK);
    CHECK(pool.slots[id].frame.checksum_fnv1a==coop_fnv1a(gray,9216));
    CHECK(coop_read_begin(&pool,id,generation,&pool.slots[id].frame)==COOP_OK);
    CHECK(coop_read_release(&pool,id,generation)==COOP_OK);
    replay.steps=steps; replay.count=3; replay.virtual_ms=0xfffffffeu;
    c3_bind_replay(&h,&replay);
    CHECK(c3_i2c_write_read(&h,0,0x45,cmd,2,rx,3,100)==COOP_ENACK && replay.cursor==0);
    CHECK(c3_i2c_write_read(&h,0,0x44,cmd,2,rx,3,100)==COOP_OK && rx[2]==3);
    CHECK(c3_now_ms(&h,&i)==COOP_OK && i==3);
    memset(rx,0xcc,3);
    CHECK(c3_i2c_write_read(&h,0,0x44,cmd,2,rx,3,100)==COOP_ETIMEOUT && rx[0]==0xcc);
    CHECK(replay.virtual_ms==103 && replay.cursor==2);
    CHECK(c3_i2c_write_read(&h,0,0x44,cmd,2,rx,3,100)==COOP_ENACK && rx[0]==0xcc);
    CHECK(c3_gpio_write(&h,1,1)==COOP_OK && replay.gpio_active[1]==1);
    CHECK(c3_gpio_write(&h,1,0)==COOP_OK && replay.gpio_active[1]==0);
    printf("PASS C4/replay: %u checks, %u mock inference calls; no board data\n",checks,calls);
    return 0;
}

