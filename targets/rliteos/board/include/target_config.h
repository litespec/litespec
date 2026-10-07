/* Minimal qemu-virt board config for LiteSpec preprocessing (reconstructed). */
#ifndef TARGET_CONFIG_H
#define TARGET_CONFIG_H

/* Board memory layout (qemu -machine virt, cortex-a15, 128M) */
#define DDR_MEM_ADDR        0x40000000
#define DDR_MEM_SIZE        0x08000000
#define PERIPH_PMM_SIZE     0x01000000
#define SYS_MEM_SIZE_DEFAULT 0x04000000

/* Feature gates (pilot defaults from config/targets/liteos.yaml) */
#define LOSCFG_SYS_EXTERNAL_HEAP  0
#define LOSCFG_MEM_MUL_POOL       0
#define LOSCFG_TASK_MEM_USED      1
#define LOSCFG_MEM_FREE_BY_TASKID 0
#define LOSCFG_KERNEL_LMK         0

#endif

/* Tick rate: 100 Hz (10ms/tick) — matches the sys time-conversion tests. */
#define LOSCFG_BASE_CORE_TICK_PER_SECOND 100
