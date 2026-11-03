// Actual pinned vendor formatter, maximum uint32 timestamps and sequence.
// Tests truncation risk on the host; does not claim UART or board execution.
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "tensorflow/lite/micro/micro_string.h"
#include "c24_log_format.h"
int main() {
 char prefix[256],suffix[256],line[512];
 MicroSnprintf(prefix,sizeof(prefix),C24_FRAME_PREFIX,-7,1u,0xffffffffu,0xffffffffu,0xffffffffu,0xffffffffu);
 MicroSnprintf(suffix,sizeof(suffix),C24_FRAME_SUFFIX,-128,127,0u,0xffffffffu,0xffffffffu,0xffffffffu,0xffffffffu);
 if(strlen(prefix)>=255 || strlen(suffix)>=255 || prefix[strlen(prefix)-1]!=' ' || suffix[strlen(suffix)-1]!='\n') return 1;
 strcpy_s(line,prefix);strcat_s(line,suffix);
 if(!strstr(line,"frame_id=4294967295") || !strstr(line,"raw_fnv=0xffffffff") ||
    !strstr(line,"received_ms=4294967295") || !strstr(line,"sequence=4294967295\n")) return 2;
 printf("PASS C24 actual vendor formatter: prefix=%u suffix=%u combined=%u bytes, max uint32, 256-byte per-call bound.\n",
  (unsigned)strlen(prefix),(unsigned)strlen(suffix),(unsigned)strlen(line));
 return 0;
}
