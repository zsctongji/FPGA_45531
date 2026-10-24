#ifndef C2_DRIVER_H
#define C2_DRIVER_H
#include "cooperation_v1.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Byte offsets in the 16-bit APB3 aperture, transport ABI 2 (image ABI stays 1). */
#define C2_ID 0x43325332u
#define C2_VERSION 0x00020000u
#define C2_REG_ID 0x00u
#define C2_REG_VERSION 0x04u
#define C2_REG_STATUS 0x08u
#define C2_REG_COMMAND 0x0cu
#define C2_REG_GENERATION 0x10u
#define C2_REG_ACK 0x14u
#define C2_REG_RESPONSE 0x18u
#define C2_REG_RESPONSE_GENERATION 0x1cu
#define C2_REG_STATES 0x20u
#define C2_REG_DROPPED 0x24u
#define C2_REG_PROTOCOL_ERROR 0x28u
#define C2_REG_MAP_ENABLED 0x2cu
#define C2_REG_SHARED_BASE 0x30u
#define C2_REG_SHARED_BYTES 0x34u
#define C2_REG_VIDEO_BASE 0x38u
#define C2_REG_VIDEO_BYTES 0x3cu
#define C2_REG_DESCRIPTOR 0x40u
#define C2_CMD_ACQUIRE 3u
#define C2_CMD_RELEASE 4u
#define C2_CMD_QUERY 5u
#define C2_ECHECKSUM (-8)

typedef struct {
    void *context;
    int (*read32)(void *, uint32_t offset, uint32_t *);
    int (*write32)(void *, uint32_t offset, uint32_t);
    /* RX-only: invalidate before any image read; must not silently be a no-op. */
    int (*sync_for_cpu)(void *, uint32_t offset, uint32_t bytes);
    int (*copy_from_dma)(void *, uint32_t offset, uint8_t *, uint32_t bytes);
    void (*barrier)(void *);
} c2_io_t;
typedef struct {
    c2_io_t io;
    uint32_t poll_budget, shared_base, shared_bytes, poisoned;
} c2_driver_t;
typedef struct {
    uint32_t status, slot, generation, states, dropped, protocol_error;
    coop_frame_t frame;
} c2_reply_t;

int c2_driver_init(c2_driver_t *, const c2_io_t *, uint32_t poll_budget);
int c2_exchange(c2_driver_t *, uint32_t command, uint32_t slot, uint32_t generation, c2_reply_t *);
/* Query/acquire -> invalidate -> copy/checksum -> barrier/release.
 * Caller receives a private copy; no writable DMA pointer is exposed.
 * Timeout/bus failure poisons the service: common reset required before rebind. */
int c2_poll_copy(c2_driver_t *, uint32_t slot, uint8_t *private_gray,
                 uint32_t capacity, coop_frame_t *frame);
#ifdef __cplusplus
}
#endif
#endif
