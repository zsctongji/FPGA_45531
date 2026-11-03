// C1 diagnostics derived from the supplied Efinix static TinyML example.
// Original Efinix/TensorFlow code and model notices remain in the copied app.
#include <stdint.h>
#include <string.h>
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
#include "model/model_settings.h"
#include "model/person_image_data.h"
#include "model/no_person_image_data.h"
#include "model/people1_data.h"
#include "model/people2_data.h"
#include "model/no_people1_data.h"
#include "model/no_people2_data.h"
#include "c1_build_id.h"
#include "cooperation_v1.h"
#include "c3_hal.h"

namespace {
alignas(16) uint8_t arena[136*1024];
alignas(16) volatile uint32_t ram_probe[256];
uint32_t bits(float f) { uint32_t n; memcpy(&n,&f,4); return n; }
struct Sample { const char *name; const uint8_t *data; int bytes; bool prenormalized; int expected; };
int fail(const char *stage) {
    MicroPrintf("C1|FAIL stage=%s\n",stage);
    return 1;
}
bool ram_check() {
    const uint32_t patterns[] = {0x00000000u,0xffffffffu,0xaaaaaaaau,0x55555555u};
    for (uint32_t p : patterns) {
        for (unsigned i=0;i<256;++i) ram_probe[i]=p^i;
        for (unsigned i=0;i<256;++i) if (ram_probe[i]!=(p^i)) return false;
    }
    return true; // Small application-owned probe, not a full DDR qualification.
}
}
extern "C" int main(void) {
    bsp_init();
    MicroPrintf("C1|BOOT version=%s clint_hz=%u\n",C1_BUILD_ID,SYSTEM_CLINT_HZ);
    c3_hal_t hal;
    c3_bind_sapphire_time(&hal);
    MicroPrintf("C1|HAL capabilities=%u\n",c3_capabilities(&hal));
    if (!ram_check()) return fail("ram_probe");
    MicroPrintf("C1|RAM_PROBE words=256 status=PASS\n");
    IntcInitialize();
    static tflite::MicroErrorReporter reporter;
    const tflite::Model *model=tflite::GetModel(mobilenetv1_person_detect_model_data);
    if (model->version()!=TFLITE_SCHEMA_VERSION) return fail("schema");
    static tflite::MicroMutableOpResolver<5> ops;
    if (ops.AddAveragePool2D()!=kTfLiteOk || ops.AddConv2D()!=kTfLiteOk ||
        ops.AddDepthwiseConv2D()!=kTfLiteOk || ops.AddReshape()!=kTfLiteOk ||
        ops.AddSoftmax()!=kTfLiteOk) return fail("ops");
    static FullProfiler profiler;
    static tflite::MicroInterpreter interpreter(model,ops,arena,sizeof(arena),&reporter,&profiler);
    profiler.setInterpreter(&interpreter);
    profiler.setDump(false);
    if (interpreter.AllocateTensors()!=kTfLiteOk) return fail("allocate");
    TfLiteTensor *input=interpreter.input(0);
    if (input->type!=kTfLiteInt8 || input->dims->size!=4 ||
        input->dims->data[0]!=1 || input->dims->data[1]!=96 ||
        input->dims->data[2]!=96 || input->dims->data[3]!=1 ||
        input->bytes!=COOP_IMAGE_BYTES || interpreter.outputs_size()!=1)
        return fail("input_contract");
    TfLiteTensor *output=interpreter.output(0);
    if (output->type!=kTfLiteInt8 || output->bytes!=2 || output->dims->size!=2 ||
        output->dims->data[0]!=1 || output->dims->data[1]!=2 ||
        input->params.scale<=0.0f || output->params.scale<=0.0f) return fail("output_contract");
    if (bits(input->params.scale)!=C1_INPUT_SCALE_BITS || input->params.zero_point!=C1_INPUT_ZERO ||
        bits(output->params.scale)!=C1_OUTPUT_SCALE_BITS || output->params.zero_point!=C1_OUTPUT_ZERO)
        return fail("quantization_contract");
    MicroPrintf("C1|MODEL fnv=%x input_scale_bits=%x input_zero=%d\n",
                coop_fnv1a(mobilenetv1_person_detect_model_data,mobilenetv1_person_detect_model_data_len),
                bits(input->params.scale),input->params.zero_point);
    MicroPrintf("C1|OUTPUT scale_bits=%x zero=%d classes=2\n",bits(output->params.scale),output->params.zero_point);
    const Sample samples[]={
        {"person",g_person_data,g_person_data_size,true,1},
        {"no_person",g_no_person_data,g_no_person_data_size,true,0},
        {"people1",people1_data,people1_data_size,false,1},
        {"people2",people2_data,people2_data_size,false,1},
        {"no_people1",no_people1_data,no_people1_data_size,false,0},
        {"no_people2",no_people2_data,no_people2_data_size,false,0}
    };
    unsigned matches=0;
    for (unsigned i=0;i<6;++i) {
        const Sample &s=samples[i];
        if (s.bytes!=COOP_IMAGE_BYTES) return fail("sample_size");
        // Preserve the vendor's two distinct static-input paths exactly.
        for (int j=0;j<s.bytes;++j) {
            if (s.prenormalized) memcpy(&input->data.int8[j],&s.data[j],1);
            else input->data.int8[j]=(int8_t)((int)s.data[j]-128);
        }
        uint32_t start_ms,end_ms;
        c3_now_ms(&hal,&start_ms);
        uint32_t checksum=coop_fnv1a(input->data.int8,input->bytes);
        MicroPrintf("C1|BEGIN sample=%s frame_id=%u input_fnv=%x\n",s.name,i,checksum);
        uint64_t start_ticks=clint_getTime(BSP_CLINT);
        TfLiteStatus status=interpreter.Invoke();
        uint64_t elapsed=clint_getTime(BSP_CLINT)-start_ticks;
        c3_now_ms(&hal,&end_ms);
        if (status!=kTfLiteOk) return fail("invoke");
        int person=output->data.int8[kPersonIndex];
        int no_person=output->data.int8[kNotAPersonIndex];
        int predicted=person>no_person ? 1 : (no_person>person ? 0 : -1);
        if (predicted==s.expected) ++matches;
        MicroPrintf("C1|RESULT sample=%s invoke=0 person=%d no_person=%d predicted=%d expected=%d\n",
                    s.name,person,no_person,predicted,s.expected);
        MicroPrintf("C1|TIME sample=%s start_ms=%u end_ms=%u ticks_hi=%x ticks_lo=%x\n",
                    s.name,start_ms,end_ms,(uint32_t)(elapsed>>32),(uint32_t)elapsed);
    }
    MicroPrintf("C1|DONE samples=6 expected_matches=%u version=%s\n",matches,C1_BUILD_ID);
    // DONE means six successful Invoke calls; matches is not dataset accuracy.
    return 0;
}

