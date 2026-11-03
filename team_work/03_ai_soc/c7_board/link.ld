OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY { ram (rwx) : ORIGIN = 0x01000000, LENGTH = 64K }
SECTIONS {
 .init : { KEEP(*(.init)) } >ram
 .text : { *(.text .text.*) } >ram
 .rodata : { *(.rodata .rodata.*) } >ram
 .data : { *(.data .data.*) . = ALIGN(4); __global_pointer$ = . + 0x800; *(.sdata .sdata.*) } >ram
 .bss (NOLOAD) : { . = ALIGN(4); __bss_start = .; *(.bss .bss.* .sbss .sbss.*) *(COMMON) . = ALIGN(4); __bss_end = .; } >ram
 _stack_top = ORIGIN(ram) + LENGTH(ram);
 ASSERT(__bss_end < _stack_top - 8192, "Diagnostic leaves less than 8KiB stack")
}
