/* Minimal ARM32 reset vector + exception vectors for qemu-system-arm -machine virt.
 *
 * This is the bare-metal entry the rliteos boot harness links via `global_asm!`.
 * It sets the stack, zeroes .bss, and calls the Rust entry point `rmain`.
 *
 * Assembles with: clang --target=armv7a-none-eabi -c reset_vector.S
 */

    .section .vectors, "ax"
    .global _start
_start:
    ldr pc, =reset              /* reset vector (first word) */

    /* The remaining 7 ARM exception vectors loop forever until they are wired
     * to real handlers (see targets/rliteos/arch/task_switch.S for the context
     * switch; exception dispatch is a later arch milestone). */
    ldr pc, =hang
    ldr pc, =hang               /* undefined instruction */
    ldr pc, =hang               /* software interrupt (SVC) */
    ldr pc, =hang               /* prefetch abort */
    ldr pc, =hang               /* data abort */
    ldr pc, =hang               /* reserved */
    ldr pc, =hang               /* IRQ */
    ldr pc, =hang               /* FIQ */

    .section .text
    .global reset
reset:
    ldr sp, =__stack_top        /* boot stack from the linker script */
    /* zero .bss */
    ldr r0, =__bss_start
    ldr r1, =__bss_end
1:
    cmp r0, r1
    bge 2f
    mov r2, #0
    str r2, [r0], #4
    b   1b
2:
    bl  rmain                   /* Rust entry point (see boot harness) */
    b   hang

    .global hang
hang:
    b   hang
