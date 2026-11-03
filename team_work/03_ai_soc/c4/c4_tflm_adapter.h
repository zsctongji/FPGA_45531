#ifndef C4_TFLM_ADAPTER_H
#define C4_TFLM_ADAPTER_H
#include "c4_bridge.h"
namespace tflite { class MicroInterpreter; }
struct c4_tflm_context_t {
    tflite::MicroInterpreter *interpreter;
};
/* Caller initializes and authenticates the pinned model and accelerator first.
 * Reuses the C1 interpreter lifecycle/interrupt setup. No bus/MMIO assumptions. */
int c4_tflm_infer(void *context,const int8_t *tensor,uint32_t bytes,int8_t scores[2]);
#endif

