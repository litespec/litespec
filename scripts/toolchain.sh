#!/usr/bin/env bash
# scripts/toolchain.sh — recreate the workspace-local toolchain (.tools/ + .rustsysroot).
#
# Re-extracts the LLVM/clang/lld + QEMU `.deb` packages, rebuilds the `.tools/bin`
# symlink tree and rustc wrapper, and re-installs the bare-metal Rust std, so that
# `run.sh --clean --all` can drop `.tools`/`.rustsysroot` and this script can bring
# them back. Idempotent.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TOOLS="$ROOT/.tools"
RUSTSYSROOT="${RUSTSYSROOT:-$ROOT/../.rustsysroot}"

# Ubuntu 24.04 "noble" packages used to build the toolchain (versions are whatever
# the distro currently ships; dpkg -x only needs the package *name*).
LLVM_DEBS=(clang-18 libclang1-18 libclang-common-18-dev libclang-cpp18 libllvm18 lld-18 llvm-18-linker-tools zlib1g)
QEMU_DEBS=(qemu-system-arm qemu-system-common qemu-system-data libdaxctl1 libedit2 libfdt1 libndctl6 libpmem1 libpng16-16t64 librdmacm1t64 libslirp0 liburing2 libz3-4)

extract_debs() {
  local target="$1"; shift
  local cache="$TOOLS/apt/debs"
  mkdir -p "$cache" "$target"
  for pkg in "$@"; do
    local deb
    deb=$(ls "$cache"/${pkg}_*.deb 2>/dev/null | head -1 || true)
    if [ -z "$deb" ]; then
      echo "  toolchain: downloading $pkg ..."
      (cd "$cache" && apt-get download "$pkg") 2>/dev/null || { echo "  toolchain: WARN — could not download $pkg (skipping)"; continue; }
      deb=$(ls "$cache"/${pkg}_*.deb 2>/dev/null | head -1 || true)
    fi
    [ -n "$deb" ] && dpkg -x "$deb" "$target"
  done
}

echo "toolchain: rebuilding .tools/ (clang/lld/qemu via .deb extraction)"
rm -rf "$TOOLS/llvm-root" "$TOOLS/qemu-root"
extract_debs "$TOOLS/llvm-root" "${LLVM_DEBS[@]}"
extract_debs "$TOOLS/qemu-root" "${QEMU_DEBS[@]}"

echo "toolchain: rebuilding .tools/bin symlinks + rustc wrapper"
mkdir -p "$TOOLS/bin"
ln -sf "$TOOLS/llvm-root/usr/lib/llvm-18/bin/clang"       "$TOOLS/bin/clang"
ln -sf "$TOOLS/llvm-root/usr/lib/llvm-18/bin/clang++"     "$TOOLS/bin/clang++"
ln -sf "$TOOLS/llvm-root/usr/lib/llvm-18/bin/ld.lld"      "$TOOLS/bin/ld.lld"
ln -sf "$TOOLS/llvm-root/usr/lib/llvm-18/bin/lld"         "$TOOLS/bin/lld"
ln -sf "$TOOLS/llvm-root/usr/lib/llvm-18/bin/llvm-config" "$TOOLS/bin/llvm-config"

# Rust std: re-install the host + bare-metal target stds into the sysroot.
if command -v rustup >/dev/null 2>&1 || command -v rustc >/dev/null 2>&1; then
  echo "toolchain: installing rust-std (x86_64 + armv7a-none-eabi) into $RUSTSYSROOT"
  mkdir -p "$RUSTSYSROOT"
  rustup target add x86_64-unknown-linux-gnu armv7a-none-eabi 2>/dev/null \
    || echo "toolchain: WARN — rustup target add failed; install the stds manually"
  # Copy the std libs out of the rustup sysroot so the wrapper's --sysroot works.
  local SYSROOT
  SYSROOT="$(rustc --print sysroot 2>/dev/null || echo "")"
  if [ -n "$SYSROOT" ] && [ -d "$SYSROOT/lib/rustlib" ]; then
    cp -r "$SYSROOT/lib/rustlib/." "$RUSTSYSROOT/lib/rustlib/" 2>/dev/null || true
  fi
fi

# rustc wrapper (points the host rustc at the workspace sysroot).
cat > "$TOOLS/bin/rustc" <<EOF
#!/bin/sh
# LiteSpec portable toolchain wrapper: point rustc at the workspace sysroot that
# contains both the host std and the armv7a-none-eabi (bare-metal) std.
exec \$(command -v rustc) --sysroot=$RUSTSYSROOT "\$@"
EOF
chmod +x "$TOOLS/bin/rustc"

echo "toolchain: NOTE — 'gn' is not re-downloadable here; restore it manually from"
echo "  the OpenHarmony prebuilts (prebuilts/build-tools/<host>/bin/gn) or build from"
echo "  source (https://gn.googlesource.com/gn)."
echo "toolchain: done. Activate with: source scripts/dev-env.sh"
