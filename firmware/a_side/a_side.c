#include "a_side.h"
#include <string.h>
int a_read_gray96(const a_frame_port *p,uint8_t *image,size_t capacity,a_frame_info *info) {
    uint32_t sum=0;
    unsigned i;
    int rc;
    if(!p||!image||capacity<A_IMAGE_BYTES||!info||!p->acquire||!p->read_byte||!p->release)return -4;
    rc=p->acquire(p->context,info);
    if(rc<=0)return rc==0?1:-1;
    for(i=0;i<A_IMAGE_BYTES;i++) {
        if(p->read_byte(p->context,(uint16_t)i,&image[i])) {p->release(p->context);return -1;}
        sum+=image[i];
        if((i<2016u||i>=7200u)&&image[i]!=0) {p->release(p->context);return -3;}
    }
    p->release(p->context);
    return sum==info->checksum?0:-2;
}
uint32_t a1_crc32(uint32_t seed,const uint8_t *data,size_t n) {
    uint32_t crc=seed^0xffffffffu;
    size_t i;unsigned bit;
    for(i=0;i<n;i++) {crc^=data[i];for(bit=0;bit<8;bit++)crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);}
    return crc^0xffffffffu;
}
static void be16(uint8_t *p,uint16_t n) {p[0]=(uint8_t)(n>>8);p[1]=(uint8_t)n;}
static void be32(uint8_t *p,uint32_t n) {p[0]=(uint8_t)(n>>24);p[1]=(uint8_t)(n>>16);p[2]=(uint8_t)(n>>8);p[3]=(uint8_t)n;}
size_t a1_encode_fragment(uint8_t *out,size_t capacity,uint8_t kind,uint8_t flags,
                         uint32_t session,uint32_t event,uint32_t frame,uint32_t ms,
                         const uint8_t *body,size_t total,uint16_t index) {
    size_t offset=(size_t)index*1200u,n;
    uint16_t count=(uint16_t)((total+1199u)/1200u);
    uint32_t crc;
    if(!out||!body||flags>1u||!((kind==1u&&total==32u)||(kind==2u&&total==9216u))||index>=count)return 0;
    n=total-offset;if(n>1200u)n=1200u;
    if(capacity<40u+n)return 0;
    memcpy(out,"T3A1",4);out[4]=1;out[5]=kind;out[6]=flags;out[7]=40;
    be32(out+8,session);be32(out+12,event);be32(out+16,frame);be32(out+20,ms);
    be16(out+24,index);be16(out+26,count);be32(out+28,(uint32_t)total);
    be32(out+32,a1_crc32(0,body,total));
    memcpy(out+40,body+offset,n);
    crc=a1_crc32(0,out,36);crc=a1_crc32(crc,out+40,n);be32(out+36,crc);
    return n+40;
}
