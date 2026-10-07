#!/usr/bin/env bash
# dev-env.sh — activate the sandbox-portable toolchain for LiteSpec development.
#
# The host filesystem is read-only outside the workspace, so system packages
# (clang/lld/qemu) and rustup targets cannot be installed into /usr or /root.
# This script exposes workspace-local equivalents installed by the bring-up:
#
#   .tools/bin/            clang, ld.lld, and a rustc wrapper (armv7a-none-eabi)
#   .tools/qemu-root/      qemu-system-arm (extracted .deb + runtime libs)
#   .rustsysroot/          rust-std for x86_64 + armv7a-none-eabi
#
# Usage:
#   source scripts/dev-env.sh
#   ./run.sh test
#
# The rustc wrapper adds --sysroot=.rustsysroot so `rustc --print sysroot`
# resolves to a writable sysroot that contains the bare-metal target std.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
LLVM_ROOT="$TOOLS/llvm-root"
QEMU_ROOT="$TOOLS/qemu-root"

export PATH="$QEMU_ROOT/usr/bin:$TOOLS/bin:$PATH"
export LD_LIBRARY_PATH="$QEMU_ROOT/usr/lib/x86_64-linux-gnu:$QEMU_ROOT/usr/lib:$LLVM_ROOT/usr/lib/x86_64-linux-gnu:$LLVM_ROOT/usr/lib/llvm-18/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
