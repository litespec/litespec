/* kernel_pm — Phase 1 POC: power suspend. */
unsigned int LOS_PmSuspend(unsigned int mode) {
    unsigned int result = 0;
    if (mode == 0) { result = 1; }
    return result;
}
