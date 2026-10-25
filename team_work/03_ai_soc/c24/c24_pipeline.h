#ifndef C24_PIPELINE_H
#define C24_PIPELINE_H
#include "c2_driver.h"
#include "c4_bridge.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef int (*c24_now_fn)(void *,uint32_t *);
typedef struct {
    c4_result_t ai;
    uint32_t received_ms,infer_start_ms,infer_end_ms,person_u8,copied;
} c24_result_t;
/* Uses one hardware owner service. c2_poll_copy releases its DDR slot before
 * inference; tensors and the immutable private copy must be disjoint. */
int c24_process_next(c2_driver_t *,c4_consumer_t *,uint32_t slot,
                     uint8_t *gray,uint32_t gray_bytes,int8_t *tensor,uint32_t tensor_bytes,
                     c24_now_fn,void *clock_context,c4_infer_fn,void *infer_context,c24_result_t *);
#ifdef __cplusplus
}
#endif
#endif
