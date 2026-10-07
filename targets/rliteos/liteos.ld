/* Minimal linker script for qemu-system-arm -machine virt (ARM32).
 *
 * RAM at 0x4000_0000, 128 MB. Entry point is `_start` (reset_vector.S).
 * The boot stack (`__stack_top`) sits at the end of the image.
 */

ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x40000000, LENGTH = 128M
}

SECTIONS
{
    . = ORIGIN(RAM);

    .text : {
        KEEP(*(.vectors))      /* reset vector + exception table first */
        *(.text*)
    } > RAM

    .rodata : { *(.rodata*) } > RAM
    .data   : { *(.data*) } > RAM

    .bss : {
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    } > RAM

    . = ALIGN(8);
    __stack_top = . + 0x10000; /* 64 KB boot stack */
}
