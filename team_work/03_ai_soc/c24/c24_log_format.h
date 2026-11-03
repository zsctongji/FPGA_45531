#ifndef C24_LOG_FORMAT_H
#define C24_LOG_FORMAT_H
/* Pinned MicroPrintf has a 256-byte buffer. Emit one logical FRAME record in
 * two bounded calls; only the second ends the line. No logging ISR may interleave. */
#define C24_FRAME_PREFIX "C24|FRAME status=%d valid=%u frame_id=%u timestamp_ms=%u raw_fnv=%x tensor_fnv=%x "
#define C24_FRAME_SUFFIX "person=%d no_person=%d person_u8=%u received_ms=%u start_ms=%u end_ms=%u sequence=%u\n"
#endif
