#!/usr/bin/env bash
# rliteos target command entry point — the unique CLI for this port.
#
# The top-level ./run.sh delegates target-specific commands here:
#   ./run.sh clean  →  targets/rliteos/run.sh clean
#   ./run.sh build  →  targets/rliteos/run.sh build
#   ./run.sh qemu   →  targets/rliteos/run.sh qemu
#
# All generated artifacts live under build/ (git-ignored).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/../.." && pwd)"
cd "$DIR"

# Activate the portable toolchain (clang/rustc/ld.lld/qemu) on PATH.
# shellcheck disable=SC1091
source "$REPO/scripts/dev-env.sh"

TRIPLE="armv7a-none-eabi"
BUILD_DIR="build"
IMAGE="$BUILD_DIR/rliteos.elf"

# uv cache is workspace-local (host ~/.cache may be read-only).
export UV_CACHE_DIR="${UV_CACHE_DIR:-$REPO/../.uv-cache}"

asm() {
    mkdir -p "$BUILD_DIR"
    for f in arch/*.S; do
        clang --target="$TRIPLE" -c "$f" -o "$BUILD_DIR/$(basename "$f" .S).o"
    done
    echo "assembled arch/*.S → $BUILD_DIR/"
}

emit_rust() {
    # Emit the bare-metal Rust crate. Uses a minimal smoke-test source so the
    # build is self-contained; for a full kernel port, replace the inline source +
    # function list with the combined source + the target's in-scope functions.
    mkdir -p "$BUILD_DIR"
    [ -e "$BUILD_DIR/targets" ] || ln -s "$REPO/targets" "$BUILD_DIR/targets"
    local rust_file="$DIR/$BUILD_DIR/main.rs"
    (cd "$REPO" && uv run python - "$rust_file" <<'PY'
import sys
from litespec.lowering import emit_baremetal
from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.targets import load_target
from litespec.type_mapping import load_type_model
src = b"typedef unsigned int UINT32;\nUINT32 add(UINT32 a, UINT32 b) { return a + b; }"
fns = [f.name for f in functions(parse_c(src)) if f.name]
target = load_target("liteos")
rust = emit_baremetal(src, fns, target, type_model=load_type_model("liteos"))
open(sys.argv[1], "w").write(rust)
PY
)
    echo "emitted bare-metal Rust → $rust_file"
}

build() {
    emit_rust
    asm
    # compile the Rust crate → object
    rustc --target "$TRIPLE" -C panic=abort -C debug-assertions=off --emit=obj \
        "$BUILD_DIR/main.rs" -o "$BUILD_DIR/main.o"
    # link the Rust object + arch objects into a bare-metal image
    ld.lld -T liteos.ld "$BUILD_DIR"/*.o -o "$IMAGE"
    echo "built $IMAGE"
}

clean() {
    rm -rf "$BUILD_DIR"
    echo "cleaned rliteos build artifacts (build/)"
}

qemu() {
    build
    exec qemu-system-arm -machine virt -cpu cortex-a15 -m 128M -nographic -nic none -kernel "$IMAGE"
}

case "${1:-}" in
    asm)   asm ;;
    build) build ;;
    clean) clean ;;
    qemu)  qemu ;;
    ""|-h|--help)
        echo "usage: targets/rliteos/run.sh {asm|build|clean|qemu}" ;;
    *) echo "targets/rliteos/run.sh: unknown command: ${1:-}" >&2; exit 2 ;;
esac
