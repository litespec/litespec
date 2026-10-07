#!/usr/bin/env bash
# run.sh — the sole command-dispatch entry point for LiteSpec (post-install).
#
# Usage: ./run.sh <command> [options]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# The host's ~/.cache is read-only; use the workspace uv cache (dev-env.sh also
# relies on this). Respect an explicit UV_CACHE_DIR if already set.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/../.uv-cache}"

# Resolve uv robustly: PATH first, then common non-interactive-PATH locations
# (conda, cargo, ~/.local, /usr/local). SSH non-interactive shells often lack
# these on PATH, which otherwise yields "uv: command not found".
UV_BIN=""
if command -v uv >/dev/null 2>&1; then
  UV_BIN="uv"
else
  for c in "$HOME/miniconda3/bin/uv" "$HOME/miniconda/bin/uv" "$HOME/.cargo/bin/uv" "$HOME/.local/bin/uv" "/usr/local/bin/uv"; do
    if [ -x "$c" ]; then UV_BIN="$c"; break; fi
  done
fi
if [ -z "$UV_BIN" ]; then
  echo "run.sh: 'uv' not found; install it (https://docs.astral.sh/uv/) or add it to PATH" >&2
  exit 2
fi
UV="$UV_BIN run"

usage() {
  cat <<'EOF'
Usage: ./run.sh <command> [options]

Pipeline commands:
  validate, extract, lower, lower-to-rust, decompose, emit-isir, verify
  verify-ec, verify-isir, verify-contracts, lift, check, schema, conformance
  coverage, generate-tests, generate-combined, pipeline
  isir-completeness, ec-completeness, build-gn, repo-init, pin, update-pin
  fetch-source, test, format, shell

Target commands (delegate to targets/<port>/run.sh):
  build, qemu, asm

Workspace:
  clean          caches + artifacts + third_party/ (keeps .venv + uv caches)
  clean --all    also removes .venv + uv caches (full reset)
EOF
}

CMD="${1:-}"
shift 2>/dev/null || true

# Full test run: activate the portable toolchain (clang/ld.lld/qemu), generate the
# combined-source fan-out (so the 56 combined-source integration tests execute
# rather than skip), then run pytest.
run_full_tests() {
  source scripts/dev-env.sh
  for m in kernel_mm bitmap list mux event queue sem sys task sched swtmr arch_mmu pm; do
    $UV python scripts/generate_combined_sources.py "$m" --out /tmp >/dev/null
  done
  for n in 2 3 4 5; do cp /tmp/los_task_combined.c /tmp/los_task${n}_combined.c; done
  for n in 2 3 4; do cp /tmp/los_sched_combined.c /tmp/los_sched${n}_combined.c; done
  cp /tmp/los_swtmr_combined.c /tmp/los_swtmr2_combined.c
  $UV pytest -p no:cacheprovider "$@"
}

case "$CMD" in
  validate)       $UV python -m litespec validate "$@" ;;
  extract)        $UV python -m litespec extract "$@" ;;
  lower)          $UV python -m litespec lower "$@" ;;
  lower-to-rust)  $UV python -m litespec lower-to-rust "$@" ;;
  decompose)      $UV python -m litespec decompose "$@" ;;
  emit-isir)      $UV python -m litespec emit-isir "$@" ;;
  fetch-source)   $UV python -m litespec fetch-source "$@" ;;
  verify)         $UV python -m litespec verify "$@" ;;
  verify-ec)      $UV python -m litespec verify-ec "$@" ;;
  verify-isir)    $UV python -m litespec verify-isir "$@" ;;
  verify-contracts) $UV python -m litespec verify-contracts "$@" ;;
  lift)           $UV python -m litespec lift "$@" ;;
  check)          $UV python -m litespec check "$@" ;;
  schema)         $UV python -m litespec schema "$@" ;;
  conformance)    $UV python -m litespec conformance "$@" ;;
  coverage)       $UV python -m litespec coverage "$@" ;;
  generate-tests) $UV python -m litespec generate-tests "$@" ;;
  generate-combined) $UV python scripts/generate_combined_sources.py "$@" ;;
  isir-completeness) $UV python -m litespec isir-completeness "$@" ;;
  ec-completeness)   $UV python -m litespec ec-completeness "$@" ;;
  test)           run_full_tests "$@" ;;
  format)         $UV ruff format src tests && $UV ruff check src tests ;;
  build-gn)       $UV python -m litespec build-gn "$@" ;;
  repo-init)      $UV python -m litespec repo-init "$@" ;;
  pipeline)       $UV python -m litespec pipeline "$@" ;;
  pin)            $UV python -m litespec pin "$@" ;;
  update-pin)     $UV python -m litespec update-pin "$@" ;;
  shell)          $UV bash "$@" ;;
  clean|--clean)
    # Repo-local clean: caches, generated artifacts, and the whole re-fetchable
    # third_party/ tree. Keeps .venv + .tools by default (expensive to rebuild);
    # pass --all to drop those too. Workspace-root artifacts that live OUTSIDE
    # the repo (.rustsysroot, .uv-cache) are left alone — run.sh only cleans
    # within litespec/.
    # Re-fetch with ./install.sh (Interscope) + fetch-source / repo sync.
    rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
    rm -rf librust_out.rlib kernel_mm
    rm -rf output tmp* temp*
    # Delegate the target-local clean (removes targets/<port>/build) so each
    # target owns its own build artifacts rather than hardcoding them here.
    # PYTHONDONTWRITEBYTECODE=1 so resolving the entry point below doesn't
    # re-create .pyc files mid-clean.
    entry="$(PYTHONDONTWRITEBYTECODE=1 $UV python -c "from litespec.targets import target_entrypoint; p=target_entrypoint(); print(p if p else '')")"
    if [ -n "$entry" ] && [ -x "$entry" ]; then
      "$entry" clean
    fi
    rm -rf third_party .repo-home
    if [ "${1:-}" = "--all" ]; then
      rm -rf .venv .python-version
      rm -rf .tools
      echo "cleaned workspace (--all): caches, artifacts, third_party/, .venv, .tools"
      echo "  recreate the toolchain with: ./install.sh --toolchain-install"
    else
      echo "cleaned workspace: caches, artifacts, third_party/ (kept .venv/.tools; use --all to drop them)"
    fi
    # Remove __pycache__ LAST — any Python above (entry resolution) may have
    # re-created .pyc files, so sweep them after all Python has run.
    find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
    ;;
  build|qemu|asm)
    # Delegate target-specific commands to the target's unique entry point
    # (targets/<port_name>/run.sh), resolved from config/targets/*.yaml.
    entry="$($UV python -c "from litespec.targets import target_entrypoint; p=target_entrypoint(); print(p if p else '')")"
    if [ -z "$entry" ] || [ ! -x "$entry" ]; then
      echo "run.sh: no target entry point configured (targets/<port>/run.sh)" >&2
      exit 2
    fi
    exec "$entry" "${CMD#--}"
    ;;
  ""|-h|--help|help) usage ;;
  *) echo "run.sh: unknown command: $CMD" >&2; echo; usage; exit 2 ;;
esac
