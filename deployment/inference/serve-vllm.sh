#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_MODEL_DIR:?Point VLLM_MODEL_DIR at a compatible local model directory}"
: "${VLLM_API_KEY:?Export a local API key from your secret store}"

if [[ ! -d "$VLLM_MODEL_DIR" ]]; then
  printf '%s\n' "VLLM_MODEL_DIR must be an existing directory." >&2
  exit 1
fi

exec vllm serve "$VLLM_MODEL_DIR" \
  --host 127.0.0.1 \
  --port "${VLLM_PORT:-8000}" \
  --served-model-name Qwen3.8 \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-262144}" \
  --max-num-seqs 3 \
  --max-num-batched-tokens 4096 \
  --kv-cache-dtype fp8 \
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION:-0.98}" \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser qwen3
