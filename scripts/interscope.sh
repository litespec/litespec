#!/usr/bin/env bash
# scripts/interscope.sh — clone/verify the InterScope dependency and record its pin.
#
# Clones InterScope from INTERSCOPE_REPO (default https://github.com/ywci/interscope)
# into third_party/interscope when absent, verifies the entry point + schema, and records
# the pinned commit into config/interscope/interscope_pin.yaml.
#
# Flags:
#   --configure-llm          auto-detect an available LLM API key and set the
#                            provider in conf/config.yaml (api_key uses ${VAR})
#   --configure-llm=<p>      force a provider: deepseek | openai | anthropic
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IS_ROOT="${ROOT}/third_party/interscope"

# The InterScope official repo is configurable in config/interscope/interscope_pin.yaml
# (``interscope.repo``); INTERSCOPE_REPO overrides it (e.g. a mirror). The default
# fallback is the official GitHub site.
read_repo() {
    python3 - "${ROOT}/config/interscope/interscope_pin.yaml" <<'PY' 2>/dev/null
import sys
try:
    import yaml
    data = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
    print((data.get("interscope") or {}).get("repo", ""))
except Exception:
    print("")
PY
}
IS_REPO="${INTERSCOPE_REPO:-$(read_repo)}"
IS_REPO="${IS_REPO:-https://github.com/ywci/interscope}"

CONFIGURE_LLM=0
LLM_PROVIDER=""
for arg in "$@"; do
    case "$arg" in
        --configure-llm) CONFIGURE_LLM=1 ;;
        --configure-llm=*) CONFIGURE_LLM=1; LLM_PROVIDER="${arg#--configure-llm=}" ;;
        *) echo "interscope.sh: unknown flag: $arg" >&2; exit 2 ;;
    esac
done

if [ ! -d "${IS_ROOT}" ]; then
    echo "interscope: cloning ${IS_REPO}"
    git clone "${IS_REPO}" "${IS_ROOT}"
fi

if [ ! -x "${IS_ROOT}/run.sh" ]; then
    echo "interscope: entry point ${IS_ROOT}/run.sh not found" >&2
    exit 1
fi
if [ ! -f "${IS_ROOT}/conf/schemas/isir_schema.yaml" ]; then
    echo "interscope: schema ${IS_ROOT}/conf/schemas/isir_schema.yaml not found" >&2
    exit 1
fi

SHA="$(git -C "${IS_ROOT}" rev-parse HEAD 2>/dev/null || echo "unknown")"
# Preserve the configured repo (so the official-site setting survives re-pin).
printf 'interscope:\n  repo: %s\n  commit: %s\n  isir_schema_version: "0.1"\n' \
  "${IS_REPO}" "${SHA}" > "${ROOT}/config/interscope/interscope_pin.yaml"
echo "interscope: pinned ${SHA} from ${IS_REPO}"

# Install InterScope's own dependencies (uv venv + Python deps + opam/OCaml).
# Best-effort: a missing/failing opam install must not undo the recorded pin.
# --install-koika-switch lets the installer create the dedicated Kōika opam switch
# (OCaml 4.14.2 + Coq 8.18) instead of erroring out on the version mismatch.
echo "interscope: installing its dependencies (uv venv + opam + Kōika switch)..."
if ! bash "${IS_ROOT}/install.sh" --install-koika-switch; then
    echo "interscope: WARNING — dependency install failed (opam/OCaml); pin recorded anyway" >&2
fi

detect_llm() {
    # Preferred default is DeepSeek when DEEPSEEK_API_KEY is non-empty;
    # OpenAI and Anthropic are fallbacks. All checks require a non-empty value.
    if [ -n "${DEEPSEEK_API_KEY:-}" ]; then echo "deepseek"
    elif [ -n "${OPENAI_API_KEY:-}" ]; then echo "openai"
    elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then echo "anthropic"
    else echo ""; fi
}

ollama_available() {
    # ollama serves the OpenAI-compatible API on localhost:11434 by default.
    command -v curl >/dev/null 2>&1 && \
        curl -fsS --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1
}

configure_llm() {
    local cfg="${IS_ROOT}/conf/config.yaml"
    [ -f "$cfg" ] || { echo "interscope: no conf/config.yaml to configure" >&2; return 0; }
    local provider="${LLM_PROVIDER:-$(detect_llm)}"
    if [ -z "$provider" ]; then
        if ollama_available; then
            echo "interscope: no LLM API key detected; local ollama server is reachable — keeping llm.provider=ollama"
        else
            echo "interscope: no LLM API key (DEEPSEEK_API_KEY/OPENAI_API_KEY/ANTHROPIC_API_KEY) and no local ollama server — llm.provider left as-is; proof automation will fail until a provider is configured" >&2
        fi
        return 0
    fi
    python3 - "$cfg" "$provider" <<'PY'
import re, sys

cfg_path, provider = sys.argv[1], sys.argv[2].lower()
PRESETS = {
    "deepseek":  ("deepseek", "deepseek-chat", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1"),
    "openai":    ("openai", "gpt-4o-mini", "OPENAI_API_KEY", "https://api.openai.com/v1"),
    "anthropic": ("anthropic", "claude-sonnet-4-5", "ANTHROPIC_API_KEY", None),
}
if provider not in PRESETS:
    print(f"interscope: unsupported LLM provider {provider!r} (deepseek|openai|anthropic)", file=sys.stderr)
    sys.exit(2)

name, model, key_env, base_url = PRESETS[provider]
text = open(cfg_path, encoding="utf-8").read()

def set_key(key, value):
    # replace the first occurrence (the top-level llm: block's key)
    return re.sub(r'(?m)^(\s*' + key + r':\s*)"[^"]*"',
                  lambda m: m.group(1) + '"' + value + '"', text, count=1)

text = set_key("provider", name)
text = set_key("model", model)
text = set_key("api_key", "${" + key_env + "}")
endpoint = base_url if base_url else "(SDK default endpoint)"
if base_url:
    text = set_key("base_url", base_url)

open(cfg_path, "w", encoding="utf-8").write(text)
print(f"interscope: LLM provider updated → provider={name}, model={model}, api_key=${{{key_env}}}, base_url={endpoint}")
PY
}

if [ "$CONFIGURE_LLM" = 1 ]; then
    configure_llm
else
    # best-effort hint without mutating the clone
    local_provider="$(detect_llm)"
    if [ -n "$local_provider" ]; then
        echo "interscope: ${local_provider}_API_KEY detected — run with --configure-llm to switch conf/config.yaml"
    elif ollama_available; then
        echo "interscope: no LLM API key detected; local ollama server is reachable — default llm.provider=ollama"
    else
        echo "interscope: no LLM API key and no local ollama server — set DEEPSEEK_API_KEY/OPENAI_API_KEY/ANTHROPIC_API_KEY (or run a local ollama) to enable proof automation"
    fi
fi
