#include "c3_thermal_publish.h"
#include <string.h>
int c3_publish_thermal(const c3_hal_t *hal,const coop_thermal_t *input,uint32_t policy,
                      coop_thermal_t *out,c3_thermal_quality_t *quality) {
    coop_thermal_t snapshot;c3_thermal_quality_t q;uint32_t now,i,count=0;int rc;
    if(!input || !out || !quality || policy>C3_THERMAL_ALLOW_BAD_620) return COOP_EINVAL;
    if(!(c3_capabilities(hal)&C3_CAP_CHECKED_TIME)) return COOP_ENOTSUP;
    snapshot=*input;
    if(snapshot.abi_version!=COOP_ABI_VERSION) return COOP_EINVAL;
    for(i=0;i<768;i++) count+=(snapshot.pixel_valid_bits[i/8]>>(i%8))&1u;
    if(count==768) {
        if(snapshot.valid_flags!=COOP_SAMPLE_VALID || snapshot.error_bits) return COOP_ESTATE;
        q.quality=C3_THERMAL_QUALITY_FULL;
    } else {
        if(policy!=C3_THERMAL_ALLOW_BAD_620 || count!=767 || snapshot.valid_flags!=3u ||
           snapshot.error_bits!=COOP_ERROR_PIXEL_QUALITY || snapshot.temperature_centi_c[620]!=0)
            return COOP_ESTATE;
        for(i=0;i<768;i++)
            if(((snapshot.pixel_valid_bits[i/8]>>(i%8))&1u)!=(i==620?0u:1u)) return COOP_ESTATE;
        q.quality=C3_THERMAL_QUALITY_MASKED;
    }
    rc=c3_now_ms(hal,&now);if(rc) return rc;
    if(!coop_age_valid(now,snapshot.timestamp_ms,COOP_THERMAL_MAX_LAG_MS)) return COOP_ETIMEOUT;
    q.valid_pixels=count;q.age_ms=now-snapshot.timestamp_ms;
    *out=snapshot;*quality=q;return COOP_OK;
}
