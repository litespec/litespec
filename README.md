# LiteSpec

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![python-ci](https://github.com/litespec/litespec/actions/workflows/python-ci.yml/badge.svg)](https://github.com/litespec/litespec/actions/workflows/python-ci.yml)

LiteSpec is a unified software-level specification and lowering framework:

```
C source ──► LIR ──► Rust ──► ISIR ──► [InterScope](https://github.com/ywci/interscope) (ITP / model checking)
```

It lowers real LiteOS-A / OpenHarmony kernel code (task, scheduler, timer, mutex,
memory, IPC, and the ARM arch-MMU) to a word-addressable Rust port (`rliteos`),
with layered equivalence checking (C↔LIR, LIR↔Unsafe, Unsafe↔Safe, LIR↔ISIR) and
arch-neutral interface contracts for cross-arch (ARM/x86/RISC-V) conformance.

## LIR

**LIR** (LiteSpec Intermediate Representation) is the central IR between the C
source and the Rust port. Its semantics is a labelled transition system
`(Σ, Init, →)`, with two node families:

- **`Expr`** (pure) — `IntLit`, `BoolLit`, `Var`, `Call`, `BinOp`, `Not`,
  `Compare`, `Field`, `Deref`, `AddrOf`, `Index`, `Ternary`.
- **`EffectExpr`** (side-effecting) — `Sequence`, `Assign`, `SetUpdate`, `Skip`,
  `Conditional`, `Let`, `Quantified`, `While`, `ForRange`, `ForC`, `DoWhile`,
  `LabeledBlock`/`BreakLabel`, `Iterator`, `CallEffect`, `Guard`, `Return`.

A few examples:

| node | example |
|---|---|
| `IntLit` / `Var` | `IntLit(42)` / `Var("x")` |
| `BinOp` | `BinOp(Var("x"), "+", Var("y"))` |
| `Field` / `Deref` / `AddrOf` | `Field(Var("p"), "next")` / `Deref(Var("p"))` / `AddrOf(Var("x"))` |
| `Assign` | `Assign("x", IntLit(1))` |
| `Sequence` | `Sequence([s1, s2])` |
| `Conditional` | `Conditional(cond, then_, else_)` |
| `CallEffect` | `CallEffect("LOS_MemAlloc", [Var("pool"), Var("size")])` |

The word model is parameterized by `word_bits` (32 or 64): it drives `Nat` →
`u32`/`u64` in the Rust lowering, the interpreter's arithmetic mask, and the
memory/pointer model. A scope model provides `fv`/`bound`/`substitute`/
typing-context, and `litespec.lir.wellformedness` checks well-formedness.

Pipeline role:

```
C ──extract──► LIR ──lower──► Rust (unsafe) ──► Rust (safe) ──abstract──► ISIR
```

Each seam is checked independently: C↔LIR, LIR↔Unsafe, Unsafe↔Safe, LIR↔ISIR.

The Rust lowering has two stages: **unsafe Rust** is the direct, raw-pointer
translation of the C — `unsafe` blocks and `read_volatile`/`write_volatile` MMIO
that preserve the C memory/pointer semantics — and **safe Rust** wraps that core
in a safe interface with explicit invariants. The `Unsafe↔Safe` seam proves the
two are observationally equivalent.

## Status

Every integration test — task, scheduler, swtmr, mutex, memory, arch-MMU
page-table walk, SMP primitives, cross-arch contracts, and the
`qemu-system-arm` boot test — runs against the real LiteOS-A sources.

The `kernel_mm` allocator (`LOS_MemAlloc`/`LOS_MemFree`/`LOS_MemAllocAlign`) plus
`kernel_sched`/`kernel_ipc`/`kernel_pm` are EC-complete and ISIR-complete;
`kernel_vm` (`LOS_ArchMmuQuery`) is ISIR-complete.

## Install

```bash
./install.sh                   # Python environment (uv) + InterScope
./install.sh --interscope-only # InterScope only
```

The portable toolchain (clang/lld, `armv7a-none-eabi` Rust, qemu) is activated
with `source scripts/dev-env.sh`.

## Commands

Everything goes through `./run.sh <command> [args]`. The portable toolchain is
auto-activated for the commands that need it.

| command | description |
|---|---|
| `validate`, `extract`, `lower`, `lower-to-rust` | validate a spec → extract C→LIR → emit Rust (`lower` is an alias of `lower-to-rust`) |
| `decompose`, `emit-isir`, `verify` | Hoare decomposition → emit `.isir` → verify a ported target |
| `verify-ec`, `verify-isir`, `verify-contracts` | equivalence checking / InterScope property check / interface contracts |
| `conformance` | conformance check |
| `coverage`, `generate-tests`, `generate-combined` | coverage / generate tests / combined C source |
| `pipeline`, `isir-completeness`, `ec-completeness` | run the pipeline / ISIR completeness / EC completeness |
| `build-gn`, `repo-init`, `pin` | OpenHarmony `BUILD.gn` / repo manifest / InterScope commit pin |
| `fetch-source`, `test`, `format`, `shell` | fetch sources / run tests / format / shell |
| **Target** (delegates to `targets/<port>/run.sh`) | |
| `build` | emit → compile → assemble → link → `build/<port>.elf` |
| `qemu` | build + boot in QEMU |
| `asm` | assemble the arch `.S` files |
| `clean` | caches + artifacts + `third_party/` (keeps `.venv`/`.tools`); `--all` = full repo reset |

## Glossary

| term | meaning |
|---|---|
| `fv` / `bound` | free variables / bound (binding) variables of an expression |
| `substitute` | capture-avoiding substitution |
| `word_bits` | machine word width (32 or 64) |
| `Nat` | the machine-word integer type (`u32`/`u64`) |
| EC-complete | all equivalence-checking seams discharged |
| ISIR-complete | every in-scope function has an emitted `.isir` |

## License

MIT Licensed - See [LICENSE](LICENSE) for details.

