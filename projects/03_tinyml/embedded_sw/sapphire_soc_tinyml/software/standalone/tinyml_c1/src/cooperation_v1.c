#include "cooperation_v1.h"
#include <string.h>

uint32_t coop_fnv1a(const void *data, size_t bytes) {
    const uint8_t *p = (const uint8_t *)data;
    uint32_t value = 2166136261u;
    while (bytes--) { value ^= *p++; value *= 16777619u; }
    return value;
}
int coop_age_valid(uint32_t ref, uint32_t sample, uint32_t max_age) {
    uint32_t delta = ref - sample;
    return max_age < 0x80000000u && delta < 0x80000000u && delta <= max_age;
}
void coop_pool_init(coop_pool_t *p) {
    memset(p, 0, sizeof(*p));
}
static int slot_is(coop_pool_t *p, uint32_t id, uint32_t gen, uint32_t state) {
    return p && id < COOP_BUFFER_COUNT && p->slots[id].generation == gen &&
           p->slots[id].state == state;
}
int coop_write_begin(coop_pool_t *p, uint32_t *id, uint32_t *gen) {
    uint32_t i;
    if (!p || !id || !gen) return COOP_EINVAL;
    for (i = 0; i < COOP_BUFFER_COUNT; ++i) {
        if (p->slots[i].state == COOP_FREE) {
            p->slots[i].state = COOP_WRITING;
            ++p->slots[i].generation;
            *id = i; *gen = p->slots[i].generation;
            return COOP_OK;
        }
    }
    ++p->dropped_new_frames;
    return COOP_EBUSY;
}
int coop_write_commit(coop_pool_t *p, uint32_t id, uint32_t gen,
                      const coop_frame_t *f) {
    if (!f || !slot_is(p,id,gen,COOP_WRITING)) return COOP_ESTATE;
    if (f->abi_version != COOP_ABI_VERSION || f->buffer_id != id ||
        f->data_offset != (id ? COOP_IMAGE1_OFFSET : COOP_IMAGE0_OFFSET) ||
        f->data_bytes != COOP_IMAGE_BYTES || f->format != COOP_FORMAT_GRAY8 ||
        f->stride != COOP_IMAGE_W || !(f->valid_flags & COOP_VALID_COMPLETE) ||
        (f->valid_flags & ~(COOP_VALID_COMPLETE|COOP_VALID_MOTION|COOP_VALID_BBOX)) ||
        f->reserved || f->motion_count > 96u*54u ||
        ((f->valid_flags & COOP_VALID_BBOX) &&
         (!(f->valid_flags & COOP_VALID_MOTION) || f->bbox_x0 > f->bbox_x1 ||
          f->bbox_y0 > f->bbox_y1 || f->bbox_x1 >= 96u || f->bbox_y1 >= 54u)))
        return COOP_EINVAL;
    p->slots[id].frame = *f;
    p->slots[id].state = COOP_READY;
    return COOP_OK;
}
int coop_write_abort(coop_pool_t *p,uint32_t id,uint32_t gen) {
    if (!slot_is(p,id,gen,COOP_WRITING)) return COOP_ESTATE;
    p->slots[id].state = COOP_FREE; return COOP_OK;
}
int coop_read_begin(coop_pool_t *p,uint32_t id,uint32_t gen,coop_frame_t *f) {
    if (!f || !slot_is(p,id,gen,COOP_READY)) return COOP_ESTATE;
    *f = p->slots[id].frame; p->slots[id].state = COOP_READING; return COOP_OK;
}
int coop_read_release(coop_pool_t *p,uint32_t id,uint32_t gen) {
    if (!slot_is(p,id,gen,COOP_READING)) return COOP_ESTATE;
    p->slots[id].state = COOP_FREE; return COOP_OK;
}

