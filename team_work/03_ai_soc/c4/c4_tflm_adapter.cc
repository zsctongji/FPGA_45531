#include "c4_tflm_adapter.h"
#include <string.h>
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/c/common.h"
static uint32_t float_bits(float f) { uint32_t u; memcpy(&u,&f,4); return u; }
int c4_tflm_infer(void *context,const int8_t *tensor,uint32_t bytes,int8_t scores[2]) {
    c4_tflm_context_t *c=static_cast<c4_tflm_context_t *>(context);
    if(!c || !c->interpreter || !tensor || !scores || bytes!=9216) return COOP_EINVAL;
    if(c->interpreter->inputs_size()!=1 || c->interpreter->outputs_size()!=1) return COOP_EINVAL;
    auto *in=c->interpreter->input(0);
    auto *out=c->interpreter->output(0);
    if(in->type!=kTfLiteInt8 || in->bytes!=9216 || in->dims->size!=4 ||
       in->dims->data[0]!=1 || in->dims->data[1]!=96 || in->dims->data[2]!=96 ||
       in->dims->data[3]!=1 || out->type!=kTfLiteInt8 || out->bytes!=2 ||
       out->dims->size!=2 || out->dims->data[0]!=1 || out->dims->data[1]!=2 ||
       float_bits(in->params.scale)!=0x3c008081u || in->params.zero_point!=-1 ||
       float_bits(out->params.scale)!=0x3b800000u || out->params.zero_point!=-128)
        return COOP_EINVAL;
    memcpy(in->data.int8,tensor,bytes);
    if(c->interpreter->Invoke()!=kTfLiteOk) return COOP_EIO;
    scores[0]=out->data.int8[0]; scores[1]=out->data.int8[1];
    return COOP_OK;
}

