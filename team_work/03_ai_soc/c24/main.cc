// C2/C4 integration app: pinned vendor TFLM model, private RX copies, no software
// ownership pool. Default build runs a synthetic static self-test then disables
// live MMIO until physical mapping and shared time have actually been verified.
#include <stdint.h>
#include "bsp.h"
#include "intc.h"
#include "tinyml.h"
#include "ops/ops_api.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/debug_log.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "platform/tinyml/profiler.h"
#include "model/mobilenetv1_person_detect_model_data.h"
#include "c24_build_id.h"
#include "c24_pipeline.h"
#include "c24_log_format.h"
#include "c2_sapphire.h"
#include "c3_hal.h"
#include "c3_shared_time.h"
#include "c4_tflm_adapter.h"
namespace {
alignas(16) uint8_t arena[136*1024],gray[9216];
alignas(16) int8_t tensor[9216];
struct RuntimeConfig {uint32_t live,map_verified,shared_time_verified,shared_base;};
// Volatile reads retain both firmware paths in the linked default image.
const volatile RuntimeConfig config={C24_ENABLE_LIVE,C24_MAP_VERIFIED,C24_SHARED_TIME_VERIFIED,C24_SHARED_BASE};
int fail(const char *stage,int status) {MicroPrintf("C24|FAIL stage=%s status=%d\n",stage,status);return 1;}
struct LiveInference {c4_tflm_context_t *model;uint32_t sequence;};
int live_infer(void *context,const int8_t *input,uint32_t bytes,int8_t scores[2]) {
 LiveInference *live=static_cast<LiveInference *>(context);++live->sequence;
 MicroPrintf("C24|INFER_BEGIN sequence=%u\n",live->sequence);
 int status=c4_tflm_infer(live->model,input,bytes,scores);
 MicroPrintf("C24|INFER_END sequence=%u status=%d\n",live->sequence,status);
 return status;
}
}
extern "C" int main(void) {
 bsp_init();
 MicroPrintf("C24|BOOT version=%s policy=pad54_candidate source=synthetic_selftest live=%u map_verified=%u shared_time_verified=%u transport=%x clint_hz=%u\n",
  C24_BUILD_ID,config.live,config.map_verified,config.shared_time_verified,C2_VERSION,(uint32_t)BSP_CLINT_HZ);
 IntcInitialize();
 const tflite::Model *model=tflite::GetModel(mobilenetv1_person_detect_model_data);
 if(model->version()!=TFLITE_SCHEMA_VERSION) return fail("schema",-1);
 if(coop_fnv1a(mobilenetv1_person_detect_model_data,mobilenetv1_person_detect_model_data_len)!=C24_MODEL_FNV)
   return fail("model_identity",-1);
 MicroPrintf("C24|MODEL fnv=%x\n",C24_MODEL_FNV);
 static tflite::MicroErrorReporter reporter;
 static tflite::MicroMutableOpResolver<5> ops;
 if(ops.AddAveragePool2D()!=kTfLiteOk || ops.AddConv2D()!=kTfLiteOk ||
    ops.AddDepthwiseConv2D()!=kTfLiteOk || ops.AddReshape()!=kTfLiteOk || ops.AddSoftmax()!=kTfLiteOk)
   return fail("ops",-1);
 static FullProfiler profiler;
 static tflite::MicroInterpreter interpreter(model,ops,arena,sizeof(arena),&reporter,&profiler);
 profiler.setInterpreter(&interpreter);profiler.setDump(false);
 if(interpreter.AllocateTensors()!=kTfLiteOk) return fail("allocate",-1);
 c4_tflm_context_t inference={&interpreter};
 for(unsigned n=0;n<9216;n++) gray[n]=(n<2016 || n>=7200)?0:(uint8_t)((n-2016)*17+1);
 if(coop_fnv1a(gray,9216)!=C24_SELFTEST_RAW_FNV) return fail("selftest_pattern",-1);
 int status=c4_gray_to_vendor_int8(gray,9216,tensor,9216);if(status) return fail("quantize",status);
 MicroPrintf("C24|SELFTEST_BEGIN raw_fnv=%x tensor_fnv=%x synthetic=1\n",coop_fnv1a(gray,9216),coop_fnv1a(tensor,9216));
 int8_t scores[2];uint64_t start=clint_getTime(BSP_CLINT);
 status=c4_tflm_infer(&inference,tensor,9216,scores);
 uint64_t ticks=clint_getTime(BSP_CLINT)-start;
 if(status) return fail("selftest_invoke",status);
 MicroPrintf("C24|SELFTEST raw_fnv=%x tensor_fnv=%x no_person=%d person=%d person_u8=%u ticks_hi=%x ticks_lo=%x synthetic=1\n",
  coop_fnv1a(gray,9216),coop_fnv1a(tensor,9216),(int)scores[0],(int)scores[1],(uint32_t)((int)scores[1]+128),
  (uint32_t)(ticks>>32),(uint32_t)ticks);
 if(!config.live || !config.map_verified || !config.shared_time_verified) {
   MicroPrintf("C24|LIVE_DISABLED live=%u map_verified=%u shared_time_verified=%u\n",config.live,config.map_verified,config.shared_time_verified);
   MicroPrintf("C24|DONE version=%s mode=selftest\n",C24_BUILD_ID);
   return 0;
 }
 c2_io_t io;c2_sapphire_t platform;c2_driver_t driver;
 status=c2_sapphire_bind(&io,&platform,IO_APB_SLAVE_0_INPUT,config.shared_base,config.map_verified!=0);
 if(status) return fail("bind",status);
 status=c2_driver_init(&driver,&io,10000);if(status) return fail("driver_init",status);
 uint32_t capabilities=0;
 status=io.read32(io.context,C2_REG_CAPABILITIES,&capabilities);
 if(status || !(capabilities&C2_CAP_SOURCE_COMPLETION)) return fail("source_completion_capability",status?status:COOP_ENOTSUP);
 c3_shared_clock_t clock;status=c3_shared_time_bind(&clock,&io);
 if(status) return fail("shared_time_bind",status);
 uint32_t shared_now=0;status=c3_shared_now_ms(&clock,&shared_now);
 if(status) return fail("shared_time_read",status);
 c4_consumer_t consumer={};
 LiveInference live={&inference,0};
 MicroPrintf("C24|LIVE_READY version=%s capabilities=%u policy=pad54_candidate time_kind=%u time_hz=%u now_ms=%u source=c2_samples\n",
  C24_BUILD_ID,capabilities,C2_TIME_KIND_APB_MS,100000000u,shared_now);
 for(;;) for(uint32_t slot=0;slot<2;slot++) {
   c24_result_t result;
   status=c24_process_next(&driver,&consumer,slot,gray,9216,tensor,9216,c3_shared_now_ms,&clock,live_infer,&live,&result);
   if(status==COOP_EBUSY && !result.copied) continue;
   MicroPrintf(C24_FRAME_PREFIX,
     status,result.ai.valid,result.ai.frame_id,result.ai.timestamp_ms,result.ai.raw_fnv,result.ai.tensor_fnv);
   MicroPrintf(C24_FRAME_SUFFIX,
     result.ai.person,result.ai.no_person,result.person_u8,result.received_ms,result.infer_start_ms,result.infer_end_ms,live.sequence);
   if(driver.poisoned) return fail("transport_requires_common_reset",status);
 }
}
