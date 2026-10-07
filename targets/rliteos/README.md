# rliteos — LiteOS-A port board support

`targets/rliteos/` is the self-contained board support for the LiteOS-A → Rust
port (`rliteos`). It holds the target-specific *data* — assembly, linker script,
UART stub, ISIR specs, and the OpenHarmony build template — that the generic
pipeline (`src/litespec/`) consumes via `config/targets/liteos.yaml`.

## Layout

```
targets/rliteos/
├── arch/
│   ├── reset_vector.S      # ARM32 reset + exception vectors (→ rmain)
│   └── task_switch.S       # minimal HalTaskSwitch (save/restore r4–r11)
├── drivers/
│   └── uart_pl011.rs       # PL011 MMIO UART stub (prints "hello")
├── spec/                   # emitted ISIR specs (kernel_mm, kernel_sched,
│                           #   kernel_ipc, kernel_pm, and unassigned functions)
├── liteos.ld               # linker script (qemu -machine virt, RAM @0x4000_0000)
├── BUILD.gn                # OpenHarmony gn static_library("rliteos") template
├── install.sh              # dependency installer (QEMU, ARM Rust target, clang/ld.lld)
├── run.sh                  # target entry point: asm | build | clean | qemu
└── build/                  # generated artifacts (git-ignored)
```

## Commands

```sh
targets/rliteos/install.sh    # install deps (QEMU, armv7a-none-eabi Rust target, clang/ld.lld)
targets/rliteos/run.sh asm    # assemble arch/*.S → build/*.o
targets/rliteos/run.sh build  # assemble + link → build/rliteos.elf
targets/rliteos/run.sh qemu   # build + boot (prints "hello from rliteos")
targets/rliteos/run.sh clean  # remove generated artifacts (build/)
```

The top-level `./run.sh` delegates the target commands (`build`/`qemu`/`asm`) here;
`build-gn` and `fetch-source` live at the top level.

## OpenHarmony integration

`BUILD.gn` is the OpenHarmony `static_library("rliteos")` template: the ported
Rust core is pre-built to `librliteos.a` and linked into the kernel by the `gn`
build. `./run.sh build-gn liteos` emits it from `config/targets/liteos.yaml`.
Wiring it into a full OpenHarmony tree (`repo sync` + `gn gen`/`ninja`) is not yet
exercised here. The portable toolchain (clang/lld/`gn`/qemu) lives under `.tools/`
and is activated by `scripts/dev-env.sh`.
