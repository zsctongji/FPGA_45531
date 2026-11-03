#ifndef COOPERATION_V1_H
#define COOPERATION_V1_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Software ABI v1; no physical DDR/MMIO base is assigned by this header.
 * All multi-byte ABI fields are little endian, uint32_t (no C enums/pointers).
 * Only a serialized owner service may mutate the reference buffer pool. */
#define COOP_ABI_VERSION 0x00010000u
#define COOP_IMAGE_W 96u
#define COOP_IMAGE_H 96u
#define COOP_IMAGE_BYTES (COOP_IMAGE_W * COOP_IMAGE_H)
#define COOP_BUFFER_COUNT 2u
#define COOP_SHARED_BYTES 0x10000u
#define COOP_IMAGE0_OFFSET 0x1000u
#define COOP_IMAGE1_OFFSET 0x4000u
#define COOP_FORMAT_GRAY8 1u
#define COOP_VALID_COMPLETE 1u
#define COOP_VALID_MOTION 2u
#define COOP_VALID_BBOX 4u
#define COOP_SAMPLE_COMPLETE 1u
#define COOP_SAMPLE_CONVERTED 2u
#define COOP_SAMPLE_QUALITY 4u
#define COOP_SAMPLE_VALID 7u
#define COOP_ERROR_TIMEOUT 1u
#define COOP_ERROR_NACK 2u
#define COOP_ERROR_CRC 4u
#define COOP_ERROR_CALIBRATION 8u
#define COOP_ERROR_SUBFRAME 16u
#define COOP_ERROR_BUS 32u
#define COOP_ERROR_PIXEL_QUALITY 64u
#define COOP_THERMAL_MAX_LAG_MS 500u
#define COOP_ENV_MAX_LAG_MS 2000u
#define COOP_IMAGE_MAX_AGE_MS 1000u
#define COOP_FREE 0u
#define COOP_WRITING 1u
#define COOP_READY 2u
#define COOP_READING 3u
#define COOP_OK 0
#define COOP_EINVAL (-1)
#define COOP_EBUSY (-2)
#define COOP_ESTATE (-3)
#define COOP_ENOTSUP (-4)
#define COOP_ETIMEOUT (-5)
#define COOP_ENACK (-6)
#define COOP_EIO (-7)

typedef struct {
    uint32_t abi_version, frame_id, timestamp_ms, buffer_id;
    uint32_t data_offset, data_bytes, format, stride;
    uint32_t checksum_fnv1a, valid_flags, motion_count, bbox_x0;
    uint32_t bbox_y0, bbox_x1, bbox_y1, reserved;
} coop_frame_t;

typedef struct {
    uint32_t state, generation;
    coop_frame_t frame;
} coop_slot_t;

typedef struct {
    coop_slot_t slots[COOP_BUFFER_COUNT];
    uint32_t dropped_new_frames;
} coop_pool_t;

/* Complete thermal samples only: temp[i] is centi-degrees C; bad pixels have
 * validity bit 0. Invalid values must never enter heat-feature calculations. */
typedef struct {
    uint32_t abi_version, sample_id, timestamp_ms, valid_flags, error_bits;
    int16_t temperature_centi_c[768];
    uint8_t pixel_valid_bits[96];
} coop_thermal_t;
typedef struct {
    uint32_t abi_version, sample_id, timestamp_ms, valid_flags, error_bits;
    int32_t temperature_centi_c;
    uint32_t humidity_centi_percent;
} coop_environment_t;

uint32_t coop_fnv1a(const void *data, size_t bytes);
/* Future samples rejected. Max age and comparisons must be < 2^31 ms. */
int coop_age_valid(uint32_t reference_ms, uint32_t sample_ms, uint32_t max_age_ms);
void coop_pool_init(coop_pool_t *pool);
int coop_write_begin(coop_pool_t *pool, uint32_t *id, uint32_t *generation);
int coop_write_commit(coop_pool_t *pool, uint32_t id, uint32_t generation,
                      const coop_frame_t *frame);
int coop_write_abort(coop_pool_t *pool, uint32_t id, uint32_t generation);
int coop_read_begin(coop_pool_t *pool, uint32_t id, uint32_t generation,
                    coop_frame_t *frame);
int coop_read_release(coop_pool_t *pool, uint32_t id, uint32_t generation);

#ifdef __cplusplus
}
static_assert(sizeof(coop_frame_t) == 64, "frame ABI size");
#else
_Static_assert(sizeof(coop_frame_t) == 64, "frame ABI size");
#endif
#endif

