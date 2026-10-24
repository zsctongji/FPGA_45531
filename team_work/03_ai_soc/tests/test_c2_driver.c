#include "c2_driver.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {
    coop_pool_t pool;
    uint8_t ddr[COOP_SHARED_BYTES],cache[COOP_SHARED_BYTES];
    uint32_t enabled,gen,command,slot,busy,done,ticks,hang;
    uint32_t sync_skip,sync_fail,copy_fail,bad_protocol,read_fail;
    uint32_t step,acquired,synced,copied,released,barriers,commands;
    c2_reply_t response;
} fixture_t;
static fixture_t f;
static uint8_t output[COOP_IMAGE_BYTES];
static void finish(fixture_t *p) {
    int status=COOP_OK;uint32_t slot=p->slot;coop_slot_t *s=&p->pool.slots[slot];
    ++p->commands;
    if(p->command==C2_CMD_ACQUIRE) {
        status=coop_read_begin(&p->pool,slot,p->gen,&p->response.frame);
        if(!status) p->acquired=++p->step;
    } else if(p->command==C2_CMD_RELEASE) {
        status=coop_read_release(&p->pool,slot,p->gen);p->released=++p->step;
    }
    p->response.status=status==COOP_OK?0u:(status==COOP_ESTATE?2u:3u);
    p->response.slot=slot;p->response.generation=s->generation;p->response.frame=s->frame;
    p->response.states=p->pool.slots[0].state|(p->pool.slots[1].state<<2);
    p->response.dropped=p->pool.dropped_new_frames;p->response.protocol_error=p->bad_protocol;
    p->busy=0;p->done=1;
}
static int rd(void *context,uint32_t offset,uint32_t *value) {
    fixture_t *p=context;
    if(p->read_fail && offset==C2_REG_DESCRIPTOR) return COOP_EIO;
    *value=0;
    switch(offset) {
    case C2_REG_ID:*value=C2_ID;break;
    case C2_REG_VERSION:*value=C2_VERSION;break;
    case C2_REG_MAP_ENABLED:*value=p->enabled;break;
    case C2_REG_SHARED_BASE:*value=0x09010000u;break;
    case C2_REG_SHARED_BYTES:*value=COOP_SHARED_BYTES;break;
    case C2_REG_STATUS:
        if(p->busy && !p->hang && ++p->ticks>=3) finish(p);
        *value=p->busy|(p->done<<1);break;
    case C2_REG_RESPONSE:*value=p->response.status|(p->response.slot<<8);break;
    case C2_REG_RESPONSE_GENERATION:*value=p->response.generation;break;
    case C2_REG_STATES:*value=p->response.states;break;
    case C2_REG_DROPPED:*value=p->response.dropped;break;
    case C2_REG_PROTOCOL_ERROR:*value=p->response.protocol_error;break;
    default:
        if(offset<C2_REG_DESCRIPTOR || offset>C2_REG_DESCRIPTOR+60 || (offset&3u)) return COOP_EIO;
        memcpy(value,(const uint8_t *)&p->response.frame+offset-C2_REG_DESCRIPTOR,4);break;
    }
    return COOP_OK;
}
static int wr(void *context,uint32_t offset,uint32_t value) {
    fixture_t *p=context;
    switch(offset) {
    case C2_REG_GENERATION:CHECK(!p->busy && !p->done);p->gen=value;break;
    case C2_REG_COMMAND:
        CHECK(!p->busy && !p->done);p->command=value&7u;p->slot=(value>>8)&1u;p->busy=1;p->ticks=0;break;
    case C2_REG_ACK:CHECK(p->done && value==1);p->done=0;break;
    default:return COOP_EIO;
    }
    return COOP_OK;
}
static void barrier(void *context) {fixture_t *p=context;++p->barriers;++p->step;}
static int sync_rx(void *context,uint32_t offset,uint32_t bytes) {
    fixture_t *p=context;
    CHECK(p->pool.slots[offset==COOP_IMAGE1_OFFSET].state==COOP_READING);
    CHECK(bytes==COOP_IMAGE_BYTES);p->synced=++p->step;
    if(p->sync_fail) return COOP_EIO;
    if(!p->sync_skip) memcpy(p->cache+offset,p->ddr+offset,bytes);
    return COOP_OK;
}
static int copy_rx(void *context,uint32_t offset,uint8_t *dst,uint32_t bytes) {
    fixture_t *p=context;
    CHECK(p->synced>p->acquired && p->step>p->synced);
    CHECK(p->pool.slots[offset==COOP_IMAGE1_OFFSET].state==COOP_READING);
    p->copied=++p->step;
    if(p->copy_fail) return COOP_EIO;
    memcpy(dst,p->cache+offset,bytes);return COOP_OK;
}
static c2_io_t io={&f,rd,wr,sync_rx,copy_rx,barrier};
static void reset_fixture(void) {memset(&f,0,sizeof(f));f.enabled=1;}
static uint32_t publish(uint32_t seq) {
    uint32_t id,gen,n,offset;coop_frame_t frame;
    CHECK(coop_write_begin(&f.pool,&id,&gen)==0);offset=id?COOP_IMAGE1_OFFSET:COOP_IMAGE0_OFFSET;
    for(n=0;n<COOP_IMAGE_BYTES;n++) f.ddr[offset+n]=(uint8_t)(seq+n*17u);
    memset(&frame,0,sizeof(frame));frame.abi_version=COOP_ABI_VERSION;frame.frame_id=seq;
    frame.buffer_id=id;frame.timestamp_ms=seq*33u;frame.data_offset=offset;frame.data_bytes=COOP_IMAGE_BYTES;
    frame.format=COOP_FORMAT_GRAY8;frame.stride=96;frame.valid_flags=COOP_VALID_COMPLETE;
    frame.checksum_fnv1a=coop_fnv1a(f.ddr+offset,COOP_IMAGE_BYTES);
    CHECK(coop_write_commit(&f.pool,id,gen,&frame)==0);return id;
}
int main(void) {
    c2_driver_t driver;coop_frame_t frame;c2_reply_t reply;uint32_t id,n,before;
    reset_fixture();CHECK(c2_driver_init(&driver,&io,32)==0);
    for(n=1;n<=100;n++) {
        id=publish(n);
        CHECK(c2_poll_copy(&driver,id,output,sizeof(output),&frame)==0);
        CHECK(frame.frame_id==n && output[0]==(uint8_t)n && f.pool.slots[id].state==COOP_FREE);
        CHECK(f.acquired<f.synced && f.synced<f.copied && f.copied<f.released);
    }
    {uint32_t first=publish(201),second=publish(202);
     CHECK(first!=second);
     CHECK(c2_poll_copy(&driver,second,output,sizeof(output),&frame)==0 && frame.frame_id==202);
     CHECK(c2_poll_copy(&driver,first,output,sizeof(output),&frame)==0 && frame.frame_id==201);}
    CHECK(c2_poll_copy(&driver,0,output,sizeof(output),&frame)==COOP_EBUSY);
    id=publish(101);f.sync_skip=1;
    CHECK(c2_poll_copy(&driver,id,output,sizeof(output),&frame)==C2_ECHECKSUM);
    CHECK(f.pool.slots[id].state==COOP_FREE);f.sync_skip=0;
    id=publish(102);f.sync_fail=1;
    CHECK(c2_poll_copy(&driver,id,output,sizeof(output),&frame)==COOP_EIO);
    CHECK(f.pool.slots[id].state==COOP_FREE);f.sync_fail=0;
    id=publish(103);f.copy_fail=1;
    CHECK(c2_poll_copy(&driver,id,output,sizeof(output),&frame)==COOP_EIO);
    CHECK(f.pool.slots[id].state==COOP_FREE);f.copy_fail=0;
    id=publish(104);f.bad_protocol=1;
    CHECK(c2_poll_copy(&driver,id,output,sizeof(output),&frame)==COOP_EIO);
    CHECK(f.pool.slots[id].state==COOP_FREE);f.bad_protocol=0;
    before=f.commands;
    CHECK(c2_poll_copy(&driver,0,output,sizeof(output)-1,&frame)==COOP_EINVAL);
    CHECK(c2_poll_copy(&driver,0,output,sizeof(output),(coop_frame_t *)(void *)output)==COOP_EINVAL);
    CHECK(c2_poll_copy(&driver,0,(uint8_t *)(uintptr_t)0x09011000u,sizeof(output),&frame)==COOP_EINVAL);
    CHECK(f.commands==before);
    id=publish(105);CHECK(c2_exchange(&driver,3,id,f.pool.slots[id].generation+1,&reply)==COOP_ESTATE);
    CHECK(f.pool.slots[id].state==COOP_READY);
    f.hang=1;
    CHECK(c2_exchange(&driver,3,id,f.pool.slots[id].generation,&reply)==COOP_ETIMEOUT);
    CHECK(driver.poisoned==1);before=f.commands;
    f.hang=0;
    CHECK(c2_exchange(&driver,5,id,0,&reply)==COOP_ESTATE && f.commands==before);
    reset_fixture();CHECK(c2_driver_init(&driver,&io,32)==0);
    f.read_fail=1;CHECK(c2_exchange(&driver,5,0,0,&reply)==COOP_EIO && driver.poisoned);
    reset_fixture();f.enabled=0;CHECK(c2_driver_init(&driver,&io,32)==COOP_ENOTSUP);
    CHECK(driver.poisoned);reset_fixture();
    {c2_io_t missing=io;missing.sync_for_cpu=0;CHECK(c2_driver_init(&driver,&missing,32)==COOP_EINVAL);}
    printf("PASS c2_driver checks=%u frames=102 both_slots RX_readonly stale_cache_negative invalidate_copy_release failure_cleanup timeout_poison\n",checks);
    return 0;
}
