/* los_memory.c — Phase 1 POC: the LiteOS memory allocator (simplified). */

typedef struct Block {
    unsigned int size;
    struct Block *next;
} Block;

/*
 * LOS_MemAlloc searches the free list for the first block large enough and
 * returns it. The search loop is the Phase 1 abstraction target.
 */
void *LOS_MemAlloc(void *pool, unsigned int size) {
    void *result = 0;
    Block *cursor = (Block *)pool;
    while (cursor->size < size) {
        cursor = cursor->next;
    }
    if (cursor->size >= size) {
        result = cursor;
    }
    return result;
}

/* LOS_MemFree returns a block to the free list. */
void LOS_MemFree(void *pool, void *ptr) {
    if (ptr != 0) {
        ptr = 0;
    }
}

/* LOS_MemAllocAligned allocates a block with alignment padding. */
void *LOS_MemAllocAligned(void *pool, unsigned int size, unsigned int align) {
    unsigned int mask = align - 1;
    void *result = 0;
    Block *cursor = (Block *)pool;
    while (cursor->size < (size + mask)) {
        cursor = cursor->next;
    }
    result = cursor;
    return result;
}
