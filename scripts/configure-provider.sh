#!/usr/bin/env bash
# Configure Tapes proxy and OpenClaw for the chosen model provider.
# Reads: MODEL_PROVIDER  (anthropic|ollama, default: anthropic)
#        MODEL_NAME      (model id, default depends on provider)
#        OLLAMA_BASE_URL (default: http://localhost:11434)
#        OLLAMA_API_KEY  (required for ollama cloud models)
#        ANTHROPIC_API_KEY (required for anthropic)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

PROVIDER="${MODEL_PROVIDER:-anthropic}"
VM_TAPES_DIR="${1:-$SKILL_DIR/.mb/tapes}"
mkdir -p "$VM_TAPES_DIR"

case "$PROVIDER" in
  anthropic)
    MODEL="${MODEL_NAME:-claude-opus-4-6}"

    # Validate required key
    if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
        echo "ERROR: ANTHROPIC_API_KEY is required when MODEL_PROVIDER=anthropic"
        exit 1
    fi

    cat > "$VM_TAPES_DIR/config.toml" <<TOML
version = 0

[storage]

[proxy]
  provider = "anthropic"
  upstream = "https://api.anthropic.com"
  listen = ":8080"

[api]
  listen = ":8081"

[client]
  proxy_target = "http://localhost:8080"
  api_target = "http://localhost:8081"

[vector_store]

[embedding]
  dimensions = 0

[opencode]

[telemetry]
TOML
    echo "Configured Tapes for Anthropic (model: $MODEL)"
    ;;

  ollama)
    MODEL="${MODEL_NAME:-minimax-m2.7:cloud}"
    BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

    # Validate: cloud models need OLLAMA_API_KEY
    if [[ "$MODEL" == *":cloud"* ]] && [ -z "${OLLAMA_API_KEY:-}" ]; then
        echo "ERROR: OLLAMA_API_KEY is required for cloud models (MODEL_NAME=$MODEL)"
        echo "Get your key at https://ollama.com/settings"
        exit 1
    fi

    cat > "$VM_TAPES_DIR/config.toml" <<TOML
version = 0

[storage]

[proxy]
  provider = "ollama"
  upstream = "$BASE_URL"
  listen = ":8080"

[api]
  listen = ":8081"

[client]
  proxy_target = "http://localhost:8080"
  api_target = "http://localhost:8081"

[vector_store]

[embedding]
  dimensions = 0

[opencode]

[telemetry]
TOML
    echo "Configured Tapes for Ollama (model: $MODEL, upstream: $BASE_URL)"
    ;;

  *)
    echo "ERROR: Unknown MODEL_PROVIDER '$PROVIDER'. Use 'anthropic' or 'ollama'."
    exit 1
    ;;
esac

# Write provider info for start.sh to pick up
cat > "$VM_TAPES_DIR/provider.env" <<ENV
PROVIDER=$PROVIDER
MODEL=$MODEL
ENV
