#include "c4_bridge.h"
#include <string.h>
uint32_t c4_frame_size(void) { return (uint32_t)sizeof(coop_frame_t); }
uint32_t c4_pool_size(void) { return (uint32_t)sizeof(coop_pool_t); }
void c4_pool_reset(coop_pool_t *p) { if(p) coop_pool_init(p); }
int c4_publish_gray_reference(coop_pool_t *p,uint8_t *mem,uint32_t n,
                              const uint8_t *src,uint32_t bytes,uint32_t seq,uint32_t ts,
                              uint32_t *id,uint32_t *gen) {
    coop_frame_t f;
    int status;
    if(!p || !mem || n<COOP_SHARED_BYTES || !src || bytes!=COOP_IMAGE_BYTES || !id || !gen)
        return COOP_EINVAL;
    status=coop_write_begin(p,id,gen);
    if(status!=COOP_OK) return status;
    memset(&f,0,sizeof(f));
    f.abi_version=COOP_ABI_VERSION; f.buffer_id=*id; f.frame_id=seq; f.timestamp_ms=ts;
    f.data_offset=*id ? COOP_IMAGE1_OFFSET : COOP_IMAGE0_OFFSET;
    f.data_bytes=COOP_IMAGE_BYTES; f.stride=96; f.format=COOP_FORMAT_GRAY8;
    f.valid_flags=COOP_VALID_COMPLETE;
    memmove(mem+f.data_offset,src,bytes);
    f.checksum_fnv1a=coop_fnv1a(mem+f.data_offset,bytes);
    status=coop_write_commit(p,*id,*gen,&f);
    if(status!=COOP_OK) (void)coop_write_abort(p,*id,*gen);
    return status;
}
static int overlaps(const void *a,uint32_t na,const void *b,uint32_t nb) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return x<=y ? y-x<na : x-y<nb;
}
int c4_pad_gray54(const uint8_t *s,uint32_t n,uint8_t *out,uint32_t cap) {
    if (!s || !out || n!=96u*54u || cap<COOP_IMAGE_BYTES) return COOP_EINVAL;
    memmove(out+21u*96u,s,n);
    memset(out,0,21u*96u); memset(out+(21u+54u)*96u,0,21u*96u);
    return COOP_OK;
}
int c4_gray_to_vendor_int8(const uint8_t *s,uint32_t n,int8_t *out,uint32_t cap) {
    uint32_t i;
    if (!s || !out || n!=COOP_IMAGE_BYTES || cap<COOP_IMAGE_BYTES ||
        (s!=(const uint8_t *)out && overlaps(s,n,out,COOP_IMAGE_BYTES)))
        return COOP_EINVAL;
    for(i=0;i<n;++i) out[i]=(int8_t)((int16_t)s[i]-128);
    return COOP_OK;
}
int c4_process(c4_consumer_t *c,coop_pool_t *p,uint32_t id,uint32_t gen,
                const uint8_t *shared,uint32_t shared_bytes,uint32_t now,
                int8_t *tensor,uint32_t tensor_bytes,c4_infer_fn infer,
                void *context,c4_result_t *r) {
    coop_frame_t f;
    int status,release_status;
    int8_t scores[2]={0,0};
    if (!r) return COOP_EINVAL;
    memset(r,0,sizeof(*r)); r->predicted=-1; r->status=COOP_EINVAL;
    if (!c || !p) return r->status;
    status=coop_read_begin(p,id,gen,&f);
    if (status!=COOP_OK) { ++c->rejected; r->status=status; return status; }
    r->frame_id=f.frame_id; r->timestamp_ms=f.timestamp_ms;
    if (!shared || !tensor || tensor_bytes<COOP_IMAGE_BYTES ||
        overlaps(shared,shared_bytes,tensor,COOP_IMAGE_BYTES) ||
        f.abi_version!=COOP_ABI_VERSION || f.buffer_id!=id ||
        f.format!=COOP_FORMAT_GRAY8 || f.data_bytes!=COOP_IMAGE_BYTES ||
        f.stride!=96 || f.reserved || !(f.valid_flags&COOP_VALID_COMPLETE) ||
        f.data_offset!=(id ? COOP_IMAGE1_OFFSET : COOP_IMAGE0_OFFSET) ||
        f.data_offset>shared_bytes || f.data_bytes>shared_bytes-f.data_offset) {
        status=COOP_EINVAL;
    } else if (!coop_age_valid(now,f.timestamp_ms,COOP_IMAGE_MAX_AGE_MS)) {
        status=C4_ESTALE;
    } else if (c->have_last_frame &&
               ((f.frame_id-c->last_frame_id)==0 ||
                (f.frame_id-c->last_frame_id)>=0x80000000u)) {
        status=C4_EORDER;
    } else {
        r->raw_fnv=coop_fnv1a(shared+f.data_offset,f.data_bytes);
        if(r->raw_fnv!=f.checksum_fnv1a) status=C4_ECHECKSUM;
        else if(!infer) status=COOP_ENOTSUP;
        else {
            status=c4_gray_to_vendor_int8(shared+f.data_offset,f.data_bytes,tensor,tensor_bytes);
            if(status==COOP_OK) {
                r->tensor_fnv=coop_fnv1a(tensor,COOP_IMAGE_BYTES);
                status=infer(context,tensor,COOP_IMAGE_BYTES,scores);
                if(status>0) status=COOP_EIO;
            }
        }
    }
    release_status=coop_read_release(p,id,gen);
    if(release_status!=COOP_OK) status=release_status;
    if(status==COOP_OK) {
        r->no_person=scores[0]; r->person=scores[1];
        r->predicted=scores[1]>scores[0] ? 1 : (scores[0]>scores[1] ? 0 : -1);
        r->valid=1; c->last_frame_id=f.frame_id; c->have_last_frame=1; ++c->accepted;
    } else ++c->rejected;
    r->status=status; return status;
}

