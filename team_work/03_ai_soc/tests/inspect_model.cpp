// Structural inspection of the exact vendored model; no inference.
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "tensorflow/lite/schema/schema_generated.h"
#include "model/mobilenetv1_person_detect_model_data.h"
static uint32_t bits(float f) { uint32_t n; memcpy(&n,&f,4); return n; }
static void tensor(const tflite::Tensor *t) {
    printf("{\"type\":%d,\"shape\":[",(int)t->type());
    for(unsigned i=0;i<t->shape()->size();++i) printf("%s%d",i?",":"",t->shape()->Get(i));
    const auto *q=t->quantization();
    printf("],\"scale_bits\":\"%x\",\"zero\":%lld}",bits(q->scale()->Get(0)),
           (long long)q->zero_point()->Get(0));
}
int main() {
    flatbuffers::Verifier v(mobilenetv1_person_detect_model_data,mobilenetv1_person_detect_model_data_len);
    if (!tflite::VerifyModelBuffer(v)) return 1;
    const auto *m=tflite::GetModel(mobilenetv1_person_detect_model_data);
    const auto *g=m->subgraphs()->Get(0);
    printf("{\"schema_version\":%u,\"input\":",m->version());
    tensor(g->tensors()->Get(g->inputs()->Get(0)));
    printf(",\"output\":"); tensor(g->tensors()->Get(g->outputs()->Get(0)));
    printf("}\n");
    return 0;
}

