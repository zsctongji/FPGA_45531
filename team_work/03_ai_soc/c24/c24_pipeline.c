#include "c24_pipeline.h"
#include <string.h>
int c24_process_next(c2_driver_t *driver,c4_consumer_t *consumer,uint32_t slot,
                     uint8_t *gray,uint32_t gray_bytes,int8_t *tensor,uint32_t tensor_bytes,
                     c24_now_fn now,void *clock_context,c4_infer_fn infer,void *infer_context,c24_result_t *result) {
    coop_frame_t frame;int status;int8_t scores[2];uintptr_t g=(uintptr_t)gray,t=(uintptr_t)tensor;
    if(!driver || !consumer || !gray || !tensor || !now || !infer || !result ||
       gray_bytes<COOP_IMAGE_BYTES || tensor_bytes<COOP_IMAGE_BYTES || slot>=2 ||
       g>UINTPTR_MAX-COOP_IMAGE_BYTES || t>UINTPTR_MAX-COOP_IMAGE_BYTES ||
       (g<t+COOP_IMAGE_BYTES && t<g+COOP_IMAGE_BYTES)) return COOP_EINVAL;
    memset(result,0,sizeof(*result));
    status=c2_poll_copy(driver,slot,gray,gray_bytes,&frame);
    if(status==COOP_EBUSY) {result->ai.status=status;return status;}
    if(status) goto failed;
    result->copied=1;
    result->ai.frame_id=frame.frame_id;result->ai.timestamp_ms=frame.timestamp_ms;
    result->ai.raw_fnv=coop_fnv1a(gray,COOP_IMAGE_BYTES);
    status=now(clock_context,&result->received_ms);
    if(status) goto failed;
    if(!coop_age_valid(result->received_ms,frame.timestamp_ms,COOP_IMAGE_MAX_AGE_MS)) {status=C4_ESTALE;goto failed;}
    if(consumer->have_last_frame && ((frame.frame_id-consumer->last_frame_id)==0 ||
        (frame.frame_id-consumer->last_frame_id)>=0x80000000u)) {status=C4_EORDER;goto failed;}
    status=c4_gray_to_vendor_int8(gray,COOP_IMAGE_BYTES,tensor,tensor_bytes);
    if(status) goto failed;
    result->ai.tensor_fnv=coop_fnv1a(tensor,COOP_IMAGE_BYTES);
    status=now(clock_context,&result->infer_start_ms);if(status) goto failed;
    if(!coop_age_valid(result->infer_start_ms,result->received_ms,COOP_IMAGE_MAX_AGE_MS) ||
       !coop_age_valid(result->infer_start_ms,frame.timestamp_ms,COOP_IMAGE_MAX_AGE_MS)) {status=C4_ESTALE;goto failed;}
    status=infer(infer_context,tensor,COOP_IMAGE_BYTES,scores);if(status) goto failed;
    status=now(clock_context,&result->infer_end_ms);if(status) goto failed;
    if(!coop_age_valid(result->infer_end_ms,frame.timestamp_ms,COOP_IMAGE_MAX_AGE_MS) ||
       !coop_age_valid(result->infer_end_ms,result->infer_start_ms,COOP_IMAGE_MAX_AGE_MS)) {status=C4_ESTALE;goto failed;}
    result->ai.no_person=scores[0];result->ai.person=scores[1];
    result->ai.predicted=scores[1]>scores[0]?1:(scores[0]>scores[1]?0:-1);
    // Pinned output quantization: scale=1/256, zero=-128. Preserve raw INT8 too.
    result->person_u8=(uint32_t)((int32_t)scores[1]+128);
    result->ai.valid=1;result->ai.status=0;
    consumer->last_frame_id=frame.frame_id;consumer->have_last_frame=1;consumer->accepted++;
    return COOP_OK;
failed:
    if(status>0) status=COOP_EIO;
    result->ai.status=status;consumer->rejected++;return status;
}
