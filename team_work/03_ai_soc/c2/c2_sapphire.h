#ifndef C2_SAPPHIRE_H
#define C2_SAPPHIRE_H
#include "c2_driver.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {uintptr_t apb_base,shared_base;} c2_sapphire_t;
/* mappings_verified must reflect the final linker/DDR/alias integration check.
 * This function does not enable a candidate physical map or reconfigure caches. */
int c2_sapphire_bind(c2_io_t *,c2_sapphire_t *,uintptr_t apb_base,
                    uintptr_t shared_base,int mappings_verified);
#ifdef __cplusplus
}
#endif
#endif
