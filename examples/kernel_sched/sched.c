/* kernel_sched — Phase 1 POC: task scheduling. */
unsigned int LOS_Schedule(unsigned int current, unsigned int ready_mask) {
    unsigned int next = current + 1;
    if (next >= 32) { next = 0; }
    if ((ready_mask & (1u << next)) == 0) { next = current; }
    return next;
}
