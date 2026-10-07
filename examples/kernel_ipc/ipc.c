/* kernel_ipc — Phase 1 POC: message send. */
unsigned int LOS_IpcSend(unsigned int queue, unsigned int msg) {
    unsigned int result = 0;
    if (queue != 0) { result = msg; }
    return result;
}
