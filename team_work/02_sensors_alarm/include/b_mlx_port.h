#ifndef B_MLX_PORT_H
#define B_MLX_PORT_H
#include "c3_hal.h"
/* Official Melexis hooks have no context: one serialized active session only.
 * Do not call from an ISR or concurrently. HAL callback must itself time out.
 * Both elapsed-time and transaction-count bounds prevent unbounded polling. */
int b_mlx_session_begin(const c3_hal_t *, uint32_t budget_ms, uint32_t max_transactions);
int b_mlx_session_end(void);
/* end returns the ORIGINAL COOP error; official hook returns -1 on any I/O
 * failure because upstream code recognizes -MLX90640_I2C_NACK_ERROR. */
#endif
