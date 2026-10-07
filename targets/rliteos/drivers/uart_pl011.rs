// PL011 UART stub for the QEMU `virt` board (MMIO at 0x0900_0000).
//
// Bare-metal `no_std`; used by the boot harness to emit "hello" before the real
// UART driver is ported. Mirrors the MMIO lowering (`__read_mmio`/`__write_mmio`
// → `read_volatile`/`write_volatile` on the ARM target).

use core::ptr::{read_volatile, write_volatile};

const UART0_BASE: u32 = 0x0900_0000;
const UART_DR: *mut u32 = UART0_BASE as *mut u32; // data register
const UART_FR: *const u32 = (UART0_BASE + 0x18) as *const u32; // flag register
const UART_FR_TXFE: u32 = 1 << 7; // transmit FIFO empty

/// Blocking write of one byte to the PL011.
pub unsafe fn uart_putc(c: u8) {
    while read_volatile(UART_FR) & UART_FR_TXFE == 0 {}
    write_volatile(UART_DR, c as u32);
}

/// Blocking write of a string.
pub unsafe fn uart_puts(s: &str) {
    for b in s.bytes() {
        uart_putc(b);
    }
}
