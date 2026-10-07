#!/usr/bin/env bash
# install.sh — the sole installation entry point for LiteSpec.
#
# Idempotent. Creates a uv-managed Python environment and installs the InterScope
# dependency (clone → verify → pin → its own deps) by default.
#
# The sandbox-portable C/Rust/QEMU toolchain (clang/lld, armv7a-none-eabi Rust
# target, gn, qemu-system-arm) lives under .tools/ and is activated by
# scripts/dev-env.sh. Because the host filesystem is read-only outside the
# workspace, these are workspace-local .deb-extracted equivalents, not apt
# installs; `--toolchain` verifies them.
#
# Flags:
#   (none)             Python environment + InterScope (default)
#   --python-only      Python environment only
#   --interscope-only  InterScope only (clone → verify → pin → its deps)
#   --toolchain        Verify the portable toolchain under .tools/ (informational)
#   --toolchain-install  Recreate the portable toolchain (.tools/ + .rustsysroot)
#   --configure-llm=<p>  force an LLM provider: deepseek | openai | anthropic
#   --no-configure-llm   skip the automatic LLM auto-detection (default: on)
#   --rust-only        Rust toolchain + verification tools (best-effort, informational)
#   --backends-only    Verify ISIR backends (best-effort, informational)
#   --clean            Remove the virtualenv and reinstall
#
# LLM configuration is automatic by default: InterScope's conf/config.yaml is
# rewritten to use the first detected API key (DEEPSEEK_API_KEY, then OPENAI_API_KEY,
# then ANTHROPIC_API_KEY) with the key referenced via ${VAR} (never baked in). Use
# --no-configure-llm to keep the clone's default (ollama).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MODE="all"
CLEAN=0
CONFIGURE_LLM=1
LLM_PROVIDER=""
# Python version pin (override with e.g. `PY_VERSION=3.13 ./install.sh`).
PY_VERSION="${PY_VERSION:-3.12}"
for arg in "$@"; do
  case "$arg" in
    --python-only) MODE="python" ;;
    --rust-only) MODE="rust" ;;
    --interscope-only) MODE="interscope" ;;
    --backends-only) MODE="backends" ;;
    --toolchain) MODE="toolchain" ;;
    --toolchain-install) MODE="toolchain-install" ;;
    --clean) CLEAN=1 ;;
    --configure-llm) CONFIGURE_LLM=1 ;;
    --configure-llm=*) CONFIGURE_LLM=1; LLM_PROVIDER="${arg#--configure-llm=}" ;;
    --no-configure-llm) CONFIGURE_LLM=0 ;;
    *) echo "install.sh: unknown flag: $arg" >&2; exit 2 ;;
  esac
done

# Build the flags forwarded to scripts/interscope.sh.
IS_FLAGS=""
if [ "$CONFIGURE_LLM" = 1 ]; then
  IS_FLAGS="--configure-llm${LLM_PROVIDER:+=${LLM_PROVIDER}}"
fi

log() { printf '\033[1;32m[install]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[install]\033[0m %s\n' "$*" >&2; }

# Resolve uv robustly: PATH first, then common non-interactive-PATH locations
# (conda, cargo, ~/.local). SSH non-interactive shells often lack these on PATH.
if ! command -v uv >/dev/null 2>&1; then
  for c in "$HOME/miniconda3/bin" "$HOME/miniconda/bin" "$HOME/.cargo/bin" "$HOME/.local/bin"; do
    if [ -x "$c/uv" ]; then export PATH="$c:$PATH"; break; fi
  done
fi
command -v uv >/dev/null 2>&1 || {
  echo "install.sh: 'uv' is required but not found on PATH." >&2
  echo "Install it from https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
}

if [ "$CLEAN" = "1" ]; then
  log "removing .venv"
  rm -rf "$ROOT/.venv"
fi

case "$MODE" in
  all)
    log "creating uv environment (python ${PY_VERSION})"
    uv sync --extra dev --python "${PY_VERSION}"
    log "python environment ready: ${ROOT}/.venv"
    log "installing InterScope (clone → verify → pin → deps)"
    bash "$ROOT/scripts/interscope.sh" $IS_FLAGS || warn "InterScope install failed; run ./install.sh --interscope-only to retry"
    ;;
  python)
    log "creating uv environment (python ${PY_VERSION})"
    uv sync --extra dev --python "${PY_VERSION}"
    log "python environment ready: ${ROOT}/.venv"
    ;;
  rust)
    warn "Rust toolchain + verification tools (kani, verus, smack, rem, creusot) install is deferred (informational)."
    ;;
  toolchain)
    log "verifying portable toolchain under .tools/"
    for p in .tools/bin/clang .tools/bin/ld.lld .tools/qemu-root/usr/bin/qemu-system-arm .tools/bin/gn; do
      if [ -x "$p" ] || [ -f "$p" ]; then
        log "  ok: $p"
      else
        warn "  missing: $p"
      fi
    done
    if [ -d "$ROOT/../.rustsysroot/lib/rustlib/armv7a-none-eabi" ]; then
      log "  ok: armv7a-none-eabi rust-std ($ROOT/../.rustsysroot)"
    else
      warn "  missing: armv7a-none-eabi rust-std ($ROOT/../.rustsysroot)"
    fi
    log "activate with: source scripts/dev-env.sh"
    warn "components are workspace-local .deb-extracted equivalents (host /usr is read-only)"
    ;;
  toolchain-install)
    log "recreating the portable toolchain (.tools/ + .rustsysroot)"
    bash "$ROOT/scripts/toolchain.sh"
    ;;
  interscope)
    bash "$ROOT/scripts/interscope.sh" $IS_FLAGS
    ;;
  backends)
    warn "ISIR backends (koika, acl2, symbiyosys, verilator, coq, rocq) are informational."
    ;;
esac

log "done"
