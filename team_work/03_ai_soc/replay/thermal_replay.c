/* Offline ABI/policy comparison. No MMIO, UART, sensor or history writes. */
#define _CRT_SECURE_NO_WARNINGS
#include "b_sensors.h"
#include "b4_publish_gate.h"
#include "c3_thermal_publish.h"
#include <stdio.h>
#include <string.h>
_Static_assert(sizeof(coop_thermal_t)==1652,"thermal ABI");
static uint32_t clock_ms(void *context) { return *(uint32_t *)context; }
static int checked_clock(void *context,uint32_t *ms) { *ms=clock_ms(context);return COOP_OK; }
int main(int argc,char **argv) {
    FILE *file;uint32_t now=0,records=0,strict_rejected=0,masked=0,reasons;
    coop_thermal_t input,output,sentinel;uint16_t valid;
    b4_publish_config_t config;b_thermal_pair_t strict;
    c3_hal_t hal={&now,clock_ms,0,0,checked_clock};
    c3_thermal_quality_t quality;
    const uint16_t endian=1;
    if(argc!=2 || *(const unsigned char *)&endian!=1) return 2;
    file=fopen(argv[1],"rb");if(!file) return 3;
    memset(&strict,0,sizeof(strict));strict.hal=&hal;b4_publish_config_default(&config);
    for(;;) {
        size_t got=fread(&now,1,4,file);uint32_t i,count=0;
        if(!got && feof(file)) break;
        if(got!=4 || fread(&input,1,sizeof(input),file)!=sizeof(input)) {fclose(file);return 4;}
        if(input.abi_version!=COOP_ABI_VERSION || input.sample_id!=records ||
           input.valid_flags!=3 || input.error_bits!=COOP_ERROR_PIXEL_QUALITY ||
           input.temperature_centi_c[620]!=0) {fclose(file);return 5;}
        for(i=0;i<768;i++) {
            uint32_t bit=(input.pixel_valid_bits[i/8]>>(i%8))&1u;
            if(bit!=(i==620u?0u:1u)) {fclose(file);return 6;} count+=bit;
        }
        if(count!=767 || !coop_age_valid(now,input.timestamp_ms,500)) {fclose(file);return 7;}
        strict.sample=input;
        if(b_thermal_get(&strict,&output)!=COOP_ESTATE) {fclose(file);return 8;}
        strict_rejected++;
        if(b4_publish_thermal(&input,now,&config,&output,&valid,&reasons)!=COOP_OK ||
           valid!=767 || memcmp(&input,&output,sizeof(input))) {fclose(file);return 9;}
        masked++;
        if(c3_publish_thermal(&hal,&input,C3_THERMAL_ALLOW_BAD_620,&output,&quality)!=COOP_OK ||
           quality.valid_pixels!=767 || quality.quality!=C3_THERMAL_QUALITY_MASKED ||
           memcmp(&input,&output,sizeof(input))) {fclose(file);return 15;}
        if(b4_publish_thermal(&input,input.timestamp_ms+500u,&config,&output,&valid,&reasons)!=COOP_OK) {fclose(file);return 10;}
        memset(&output,0xa5,sizeof(output));sentinel=output;
        if(b4_publish_thermal(&input,input.timestamp_ms+501u,&config,&output,&valid,&reasons)!=COOP_ETIMEOUT ||
           memcmp(&sentinel,&output,sizeof(output))) {fclose(file);return 11;}
        if(b4_publish_thermal(&input,input.timestamp_ms-1u,&config,&output,&valid,&reasons)!=COOP_ETIMEOUT ||
           memcmp(&sentinel,&output,sizeof(output))) {fclose(file);return 12;}
        records++;
    }
    if(ferror(file)) {fclose(file);return 13;}fclose(file);
    if(records!=100) return 14;
    printf("{\"records\":%u,\"strict_rejected\":%u,\"B4_masked_accepted\":%u,\"C_masked_accepted\":100,\"valid_pixels\":767,\"invalid_index\":620,\"age_500_accept\":100,\"age_501_reject\":100,\"future_reject\":100}\n",
           (unsigned)records,(unsigned)strict_rejected,(unsigned)masked);
    return 0;
}
