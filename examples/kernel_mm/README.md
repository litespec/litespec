# kernel_mm examples

Phase 1 POC module: the LiteOS memory allocator.

| Example | Function |
|---|---|
| `mm_alloc_001.litespec.yaml` | `LOS_MemAlloc` |
| `mm_free_001.litespec.yaml` | `LOS_MemFree` |
| `mm_alloc_aligned_001.litespec.yaml` | `LOS_MemAllocAligned` |

These examples are added in Phase 2 (C→LIR extraction) once the extractor is in
place. Until then, see `examples/mm_search_typed_binder/` for the §18.1 worked
example exercised by the Phase 0 exit criterion.
