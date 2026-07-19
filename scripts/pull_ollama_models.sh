#!/bin/sh
# Pull chat + embedding models into the Ollama service.
# Used by the docker-compose `ollama-pull` one-shot job.
set -eu

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"
OLLAMA_EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}"

export OLLAMA_HOST

echo "Waiting for Ollama at ${OLLAMA_HOST}…"
i=0
until ollama list >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 90 ]; then
    echo "Timed out waiting for Ollama" >&2
    exit 1
  fi
  sleep 2
done

echo "Pulling chat model: ${OLLAMA_MODEL}"
ollama pull "${OLLAMA_MODEL}"

echo "Pulling embedding model: ${OLLAMA_EMBED_MODEL}"
ollama pull "${OLLAMA_EMBED_MODEL}"

echo "Ollama models ready:"
ollama list
