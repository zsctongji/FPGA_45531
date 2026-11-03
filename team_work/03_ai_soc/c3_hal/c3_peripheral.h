#ifndef C3_PERIPHERAL_H
#define C3_PERIPHERAL_H
#include "c3_hal.h"
#include "c3_shared_time.h"
#define C3_PAGE 0x1000u
#define C3_P_ID 0x00u
#define C3_P_VERSION 0x04u
#define C3_P_STATUS 0x08u
#define C3_P_COMMAND 0x0cu
#define C3_P_TX 0x10u
#define C3_P_RX 0x14u
#define C3_P_DIVISOR 0x18u
#define C3_P_TIMEOUT 0x1cu
#define C3_P_GPIO 0x20u
#define C3_P_ARM 0x24u
#define C3_P_POLARITY 0x28u
#define C3_P_MAX_ON 0x2cu
#define C3_P_ENABLED 0x30u
#define C3_P_HZ 0x34u
typedef struct {
    uint32_t bus_hz,byte_timeout_ms,poll_budget,max_alarm_on_ms,active_low_mask;
    uint32_t pins_verified;
} c3_peripheral_config_t;
/* One serialized owner. io offsets include the C3 page; clock reads use C2.
 * scratch is caller-owned RAM, disjoint from all transaction buffers, and must
 * survive the binding. RX is copied only when the complete transaction passes. */
typedef struct {
    c2_io_t io;c3_shared_clock_t clock;c3_peripheral_config_t config;
    uint8_t *scratch;uint32_t scratch_bytes,bound,poisoned,gpio;
} c3_peripheral_t;
int c3_peripheral_bind(c3_peripheral_t *,c3_hal_t *,const c2_io_t *,
                       const c3_peripheral_config_t *,uint8_t *,uint32_t);
int c3_peripheral_recover(c3_peripheral_t *,uint32_t timeout_ms);
#endif
