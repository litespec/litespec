/* Minimal ARM32 context switch for the rliteos boot harness.
 *
 * void HalTaskSwitch(LosTaskCB *newTask, LosTaskCB *runTask);
 *   r0 = newTask, r1 = runTask
 *
 * Saves the callee-saved registers + sp into runTask->stackPointer (the first
 * word of the TCB), then loads newTask->stackPointer and restores into the new
 * task. The full LiteOS-A switch also saves CPSR/SPSR and the task entry; this
 * is the minimal bring-up version.
 */

    .section .text
    .global HalTaskSwitch
HalTaskSwitch:
    push {r4-r11, lr}          /* save callee-saved + return address */
    str  sp, [r1]              /* runTask->stackPointer = sp */
    ldr  sp, [r0]              /* sp = newTask->stackPointer */
    pop  {r4-r11, pc}          /* restore and return into the new task */
