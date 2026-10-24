#ifndef C4_BRIDGE_H
#define C4_BRIDGE_H
#include "cooperation_v1.h"
#ifdef _WIN32
#define C4_API __declspec(dllexport)
#else
#define C4_API
#endif
#ifdef __cplusplus
extern "C" {
#endif
#define C4_ECHECKSUM (-8)
#define C4_ESTALE (-9)
#define C4_EORDER (-10)
typedef struct {
    uint32_t last_frame_id, have_last_frame, accepted, rejected;
} c4_consumer_t;
typedef struct {
    int32_t status;
    uint32_t valid, frame_id, timestamp_ms, raw_fnv, tensor_fnv;
    int32_t person, no_person, predicted;
} c4_result_t;
typedef int (*c4_infer_fn)(void *context, const int8_t *tensor, uint32_t bytes,
                           int8_t output_no_person_person[2]);
C4_API uint32_t c4_frame_size(void);
C4_API uint32_t c4_pool_size(void);
C4_API void c4_pool_reset(coop_pool_t *pool);
/* Host/serialized reference producer. A real DMA producer needs its own CDC,
 * memory ordering and cache protocol; this helper does not provide those. */
C4_API int c4_publish_gray_reference(coop_pool_t *, uint8_t *shared, uint32_t shared_bytes,
                                     const uint8_t *source, uint32_t source_bytes,
                                     uint32_t frame_id, uint32_t timestamp_ms,
                                     uint32_t *id, uint32_t *generation);
C4_API int c4_pad_gray54(const uint8_t *source, uint32_t bytes,
                        uint8_t *gray96, uint32_t capacity);
/* Only the pinned vendor person model preprocessing: pixel - 128.
 * This does not derive a universal INT8 conversion from the tensor zero point. */
C4_API int c4_gray_to_vendor_int8(const uint8_t *source, uint32_t bytes,
                                 int8_t *tensor, uint32_t capacity);
/* Portable serialized reference service, NOT an implemented DMA/CDC transport.
 * shared must be immutable during processing. tensor must be disjoint from shared.
 * Every acquired slot is released on success, validation error or inference error. */
C4_API int c4_process(c4_consumer_t *consumer, coop_pool_t *pool,
                      uint32_t id, uint32_t generation,
                      const uint8_t *shared, uint32_t shared_bytes,
                      uint32_t now_ms, int8_t *tensor, uint32_t tensor_bytes,
                      c4_infer_fn infer, void *context, c4_result_t *result);
#ifdef __cplusplus
}
#endif
#endif

