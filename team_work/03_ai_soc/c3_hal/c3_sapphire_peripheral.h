#ifndef C3_SAPPHIRE_PERIPHERAL_H
#define C3_SAPPHIRE_PERIPHERAL_H
#include "c3_peripheral.h"
typedef struct {uintptr_t apb_base;} c3_sapphire_io_t;
/* No DDR dependency. verified covers this APB mapping, actual IO constraints,
 * open-drain/pull-ups/electrical levels and GPIO polarity. Does not program FPGA
 * IO/pin muxes, enable unverified pads or catch CPU bus exceptions. */
int c3_sapphire_peripheral_bind(c3_peripheral_t *,c3_hal_t *,c3_sapphire_io_t *,
                                const c3_peripheral_config_t *,uint8_t *,uint32_t,int verified);
#endif
