#include "c2_driver.h"
#include <string.h>
#include <stdint.h>

static int read_reg(c2_driver_t *d, uint32_t offset, uint32_t *value) {
    return d->io.read32(d->io.context,offset,value);
}
static int status_code(uint32_t status) {
    switch(status) {case 0:return COOP_OK;case 1:return COOP_EBUSY;
    case 2:return COOP_ESTATE;case 3:return COOP_EINVAL;default:return COOP_EIO;}
}
int c2_driver_init(c2_driver_t *d,const c2_io_t *io,uint32_t budget) {
    uint32_t id,version,status,enabled,base,bytes;
    if(!d || !io || !budget || !io->read32 || !io->write32 ||
       !io->sync_for_cpu || !io->copy_from_dma || !io->barrier) return COOP_EINVAL;
    memset(d,0,sizeof(*d));d->poisoned=1;d->io=*io;d->poll_budget=budget;
    if(read_reg(d,C2_REG_ID,&id) || read_reg(d,C2_REG_VERSION,&version) ||
       read_reg(d,C2_REG_STATUS,&status) || read_reg(d,C2_REG_MAP_ENABLED,&enabled) ||
       read_reg(d,C2_REG_SHARED_BASE,&base) || read_reg(d,C2_REG_SHARED_BYTES,&bytes)) return COOP_EIO;
    if(id!=C2_ID || version!=C2_VERSION || enabled!=1) return COOP_ENOTSUP;
    if(status) return COOP_EBUSY;
    if((base&0xffffu) || bytes!=COOP_SHARED_BYTES || base>UINT32_MAX-bytes) return COOP_EINVAL;
    d->shared_base=base;d->shared_bytes=bytes;d->poisoned=0;return COOP_OK;
}
int c2_exchange(c2_driver_t *d,uint32_t command,uint32_t slot,uint32_t gen,c2_reply_t *reply) {
    uint32_t state,n,value,words[16];int error=COOP_EIO;
    if(!d || !reply || slot>=2 || (command!=3 && command!=4 && command!=5)) return COOP_EINVAL;
    if(d->poisoned) return COOP_ESTATE;
    if(read_reg(d,C2_REG_STATUS,&state)) goto uncertain;
    if(state) return COOP_EBUSY;
    memset(reply,0,sizeof(*reply));d->io.barrier(d->io.context);
    if(d->io.write32(d->io.context,C2_REG_GENERATION,gen) ||
       d->io.write32(d->io.context,C2_REG_COMMAND,command|(slot<<8))) goto uncertain;
    for(n=0;n<d->poll_budget;n++) {
        if(read_reg(d,C2_REG_STATUS,&state)) goto uncertain;
        if(state>2u) goto uncertain;
        if(state&2u) break;
    }
    if(n==d->poll_budget) {error=COOP_ETIMEOUT;goto uncertain;}
    d->io.barrier(d->io.context);
    if(read_reg(d,C2_REG_RESPONSE,&value)) goto uncertain;
    reply->status=value&3u;reply->slot=(value>>8)&1u;
    if((value&~0x103u) || reply->slot!=slot) goto uncertain;
    if(read_reg(d,C2_REG_RESPONSE_GENERATION,&reply->generation) ||
       read_reg(d,C2_REG_STATES,&reply->states) || read_reg(d,C2_REG_DROPPED,&reply->dropped) ||
       read_reg(d,C2_REG_PROTOCOL_ERROR,&reply->protocol_error)) goto uncertain;
    if(command!=C2_CMD_QUERY && !reply->status && reply->generation!=gen) goto uncertain;
    for(n=0;n<16;n++) if(read_reg(d,C2_REG_DESCRIPTOR+4*n,&words[n])) goto uncertain;
    memcpy(&reply->frame,words,sizeof(words));
    d->io.barrier(d->io.context);
    if(d->io.write32(d->io.context,C2_REG_ACK,1)) goto uncertain;
    return status_code(reply->status);
uncertain:
    d->poisoned=1;return error;
}
static int frame_valid(const coop_frame_t *f,uint32_t slot) {
    return f->abi_version==COOP_ABI_VERSION && f->buffer_id==slot &&
      f->data_offset==(slot?COOP_IMAGE1_OFFSET:COOP_IMAGE0_OFFSET) &&
      f->data_bytes==COOP_IMAGE_BYTES && f->format==COOP_FORMAT_GRAY8 && f->stride==96 &&
      (f->valid_flags&COOP_VALID_COMPLETE) && !(f->valid_flags&~7u) && !f->reserved &&
      f->motion_count<=96u*54u && (!(f->valid_flags&COOP_VALID_BBOX) ||
      ((f->valid_flags&COOP_VALID_MOTION) && f->bbox_x0<=f->bbox_x1 && f->bbox_y0<=f->bbox_y1 &&
       f->bbox_x1<96 && f->bbox_y1<54));
}
int c2_poll_copy(c2_driver_t *d,uint32_t slot,uint8_t *gray,uint32_t capacity,coop_frame_t *frame) {
    c2_reply_t q,acquired,released;int status,release_status;
    uintptr_t a,b;
    if(!d || !gray || !frame || capacity<COOP_IMAGE_BYTES || slot>=2) return COOP_EINVAL;
    a=(uintptr_t)gray;b=(uintptr_t)frame;
    if(a>UINTPTR_MAX-COOP_IMAGE_BYTES || b>UINTPTR_MAX-sizeof(*frame) ||
       (a<b+sizeof(*frame) && b<a+COOP_IMAGE_BYTES)) return COOP_EINVAL;
    if((a<(uintptr_t)d->shared_base+d->shared_bytes && a+COOP_IMAGE_BYTES>d->shared_base) ||
       (b<(uintptr_t)d->shared_base+d->shared_bytes && b+sizeof(*frame)>d->shared_base)) return COOP_EINVAL;
    status=c2_exchange(d,C2_CMD_QUERY,slot,0,&q);
    if(status) return status;
    if(((q.states>>(slot*2))&3u)!=COOP_READY) return COOP_EBUSY;
    status=c2_exchange(d,C2_CMD_ACQUIRE,slot,q.generation,&acquired);
    if(status) return status;
    if(!frame_valid(&acquired.frame,slot) || acquired.protocol_error) status=COOP_EIO;
    else {
        status=d->io.sync_for_cpu(d->io.context,acquired.frame.data_offset,COOP_IMAGE_BYTES);
        if(!status) {
            d->io.barrier(d->io.context);
            status=d->io.copy_from_dma(d->io.context,acquired.frame.data_offset,gray,COOP_IMAGE_BYTES);
            if(!status && coop_fnv1a(gray,COOP_IMAGE_BYTES)!=acquired.frame.checksum_fnv1a) status=C2_ECHECKSUM;
        }
        if(status>0) status=COOP_EIO;
    }
    /* No CPU stores to image slots are permitted. There are no RX dirty lines
       to clean on release; all accesses finish before ownership is returned. */
    d->io.barrier(d->io.context);
    release_status=c2_exchange(d,C2_CMD_RELEASE,slot,acquired.generation,&released);
    if(release_status) status=release_status;
    if(!status) *frame=acquired.frame;
    return status;
}
