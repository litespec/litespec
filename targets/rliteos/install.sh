#!/usr/bin/env bash
# Install the rliteos target dependencies: QEMU, the ARM bare-metal Rust target,
# and verify clang/ld.lld. Idempotent — safe to re-run.
#
# Cross-platform: macOS (Homebrew) and Ubuntu/Debian (apt-get).
#
# Flags:
#   --with-openharmony   also fetch the full OpenHarmony prebuilt toolchain
#                        (gn/ninja/clang) via `repo sync build` + prebuilts_download.py
#                        (multi-GB; requires `./run.sh repo-init liteos` first).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUST_TARGET="armv7a-none-eabi"
# rust-dist mirrors, tried in order (override via RUST_DIST_MIRRORS).
# rsproxy.cn is a China-accessible mirror of static.rust-lang.org; the official
# server is often slow/unreachable from China.
RUST_DIST_MIRRORS="${RUST_DIST_MIRRORS:-https://rsproxy.cn https://static.rust-lang.org}"
OS="$(uname -s)"

FETCH_OHOS=0
for arg in "$@"; do
    case "$arg" in
        --with-openharmony) FETCH_OHOS=1 ;;
        *) echo "install.sh: unknown flag: $arg" >&2; exit 2 ;;
    esac
done

fetch_dist() {
    # fetch_dist <path> <dest> — try each mirror in order; path begins with "/dist/…".
    local path="$1" dest="$2" srv
    for srv in $RUST_DIST_MIRRORS; do
        if curl -L --connect-timeout 15 --retry 2 -sSf -o "$dest" "$srv$path" 2>/dev/null; then
            return 0
        fi
    done
    return 1
}

have_arm_target() {
    local sysroot
    sysroot="$(rustc --print sysroot 2>/dev/null || true)"
    [ -n "$sysroot" ] && [ -d "$sysroot/lib/rustlib/$RUST_TARGET/lib" ]
}

install_rust_target() {
    # Try rustup (default mirror), then the RsProxy mirror, then a manual download.
    if rustup target add "$RUST_TARGET" 2>/dev/null; then
        return 0
    fi
    if RUSTUP_DIST_SERVER=https://rsproxy.cn RUSTUP_UPDATE_ROOT=https://rsproxy.cn/rustup \
        rustup target add "$RUST_TARGET" 2>/dev/null; then
        return 0
    fi
    echo "  rustup failed (mirror 404?); installing $RUST_TARGET manually" >&2
    local ver dist_ver date path sysroot tmp channel manifest
    ver="$(rustc --version | awk '{print $2}')"
    # the dist archive uses "nightly" for the nightly channel (not "1.95.0-nightly")
    dist_ver="$ver"
    case "$ver" in
        *nightly*) dist_ver="nightly" ;;
    esac
    sysroot="$(rustc --print sysroot)"
    tmp="$(mktemp -d)"
    # date for the INSTALLED version (toolchain manifest) — avoids a version/date mismatch
    manifest="$sysroot/lib/rustlib/multirust-channel-manifest.toml"
    date=""
    [ -f "$manifest" ] && date="$(awk -F'"' '/^date = /{print $2; exit}' "$manifest")"
    if [ -z "$date" ]; then
        channel="$tmp/channel.toml"
        if ! fetch_dist "/dist/channel-rust-stable.toml" "$channel"; then
            echo "ERROR: could not download channel-rust-stable.toml from any mirror" >&2
            rm -rf "$tmp"
            return 1
        fi
        date="$(awk -F'"' '/^date = /{print $2; exit}' "$channel")"
    fi
    [ -n "$date" ] || { echo "ERROR: no date in channel manifest" >&2; rm -rf "$tmp"; return 1; }
    path="/dist/$date/rust-std-$dist_ver-$RUST_TARGET.tar.xz"
    echo "  downloading rust-std-$dist_ver-$RUST_TARGET ($date)"
    if ! fetch_dist "$path" "$tmp/std.tar.xz"; then
        echo "ERROR: could not download rust-std from any mirror" >&2
        rm -rf "$tmp"
        return 1
    fi
    tar -xJf "$tmp/std.tar.xz" -C "$tmp"
    local src; src="$(find "$tmp" -type d -path "*lib/rustlib/$RUST_TARGET" | head -1)"
    [ -n "$src" ] || { echo "ERROR: rust-std layout not found in archive" >&2; rm -rf "$tmp"; return 1; }
    mkdir -p "$sysroot/lib/rustlib/$RUST_TARGET"
    cp -R "$src/." "$sysroot/lib/rustlib/$RUST_TARGET/"
    rm -rf "$tmp"
    echo "  installed $RUST_TARGET → $sysroot/lib/rustlib/$RUST_TARGET"
}

install_toolchain() {
    local need_qemu=1 need_lld=1 need_ninja=1
    command -v qemu-system-arm >/dev/null 2>&1 && need_qemu=0
    command -v ld.lld >/dev/null 2>&1 && need_lld=0
    command -v ninja >/dev/null 2>&1 && need_ninja=0
    if [ "$need_qemu" = 0 ] && [ "$need_lld" = 0 ] && [ "$need_ninja" = 0 ]; then
        return 0
    fi
    case "$OS" in
        Darwin)
            command -v brew >/dev/null 2>&1 || { echo "ERROR: Homebrew not found" >&2; exit 1; }
            brew install qemu lld ninja
            ;;
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update
                sudo apt-get install -y clang lld qemu-system-arm ninja-build
            else
                echo "ERROR: unsupported Linux package manager (need apt-get)" >&2
                exit 1
            fi
            ;;
        *)
            echo "ERROR: unsupported OS: $OS" >&2
            exit 1
            ;;
    esac
}

echo "== checking/installing QEMU + ld.lld + ninja =="
install_toolchain

echo "== installing Rust bare-metal target ($RUST_TARGET) =="
if have_arm_target; then
    echo "  $RUST_TARGET already usable"
elif command -v rustup >/dev/null 2>&1; then
    install_rust_target
    have_arm_target || { echo "ERROR: $RUST_TARGET install failed" >&2; exit 1; }
else
    echo "ERROR: rustup not found" >&2
    exit 1
fi

echo "== verifying clang + ld.lld =="
command -v clang >/dev/null 2>&1 || { echo "ERROR: clang not found" >&2; exit 1; }
command -v ld.lld >/dev/null 2>&1 || { echo "WARN: ld.lld not on PATH" >&2; }

# `gn` is not in the package managers above; OpenHarmony ships a prebuilt in
# prebuilts/build-tools/gn/ after `./run.sh fetch-source liteos`.
command -v gn >/dev/null 2>&1 || {
    echo "NOTE: 'gn' not on PATH — it ships with the OpenHarmony tree (prebuilts/build-tools)." >&2
}

install_openharmony_toolchain() {
    local ohos_dir="$ROOT/vendor/openharmony"
    local downloader="$ohos_dir/build/prebuilts_download.sh"
    if [ ! -f "$downloader" ]; then
        echo "ERROR: OpenHarmony build repo not present at $ohos_dir/build" >&2
        echo "  first run:" >&2
        echo "    ./run.sh repo-init liteos" >&2
        echo "    cd vendor/openharmony && ../../scripts/repo sync build" >&2
        exit 1
    fi
    echo "== downloading OpenHarmony prebuilt toolchain (gn/ninja/clang) =="
    # prebuilts_download.sh is the canonical entry point: it creates the venv and
    # calls prebuilts_config.py with the correct --config-file (prebuilts_download.py
    # alone expects a different, --build-arkuix config).
    (cd "$ohos_dir" && bash build/prebuilts_download.sh)
    echo "OpenHarmony toolchain under $ohos_dir/prebuilts/build-tools/"
}

if [ "$FETCH_OHOS" = 1 ]; then
    install_openharmony_toolchain
fi

echo "rliteos dependencies ready."
