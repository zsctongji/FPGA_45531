#ifndef A_SIDE_H
#define A_SIDE_H
#include <stddef.h>
#include <stdint.h>
#define A_IMAGE_BYTES 9216u
#define A_PACKET_BYTES 1240u
typedef struct { uint32_t frame_id, timestamp_ms, checksum; uint8_t buffer_id; } a_frame_info;
/* Bus callbacks must enforce a bounded hardware timeout and coherent CDC.
 * acquire returns 1=lease acquired,0=none,<0=I/O fault. Release always cleans up.
 * read_byte returns 0 on success, nonzero on fault. No guessed MMIO addresses.
 */
typedef struct {
    void *context;
    int (*acquire)(void *,a_frame_info *);
    int (*read_byte)(void *,uint16_t,uint8_t *);
    void (*release)(void *);
} a_frame_port;
/* 0=OK,1=busy,-1=port error,-2=checksum error,-3=padding error,-4=argument. */
int a_read_gray96(const a_frame_port *,uint8_t *,size_t,a_frame_info *);
/* A1 fragment: explicit big-endian writes, no C struct-padding dependence.
 * kind1=32-byte event, kind2=9216-byte GRAY8; flags bit0=SYNTHETIC.
 * Return packet size or zero for invalid arguments. Caller sends each fragment.
 */
size_t a1_encode_fragment(uint8_t *,size_t,uint8_t,uint8_t,uint32_t,uint32_t,
                         uint32_t,uint32_t,const uint8_t *,size_t,uint16_t);
uint32_t a1_crc32(uint32_t,const uint8_t *,size_t);
#endif
