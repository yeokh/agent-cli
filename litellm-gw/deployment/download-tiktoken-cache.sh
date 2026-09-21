#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# download-tiktoken-cache.sh
#
# Pre-downloads all standard tiktoken BPE encoding files into a local cache
# directory.  LiteLLM fetches these from OpenAI's CDN on first use of each
# model family; setting TIKTOKEN_CACHE_DIR makes it use the local copies
# instead, eliminating those CDN round-trips from every cold start.
#
# Encodings downloaded:
#   cl100k_base  — GPT-4, GPT-3.5-turbo, text-embedding-ada-002
#   o200k_base   — GPT-4o, GPT-4o-mini family
#   p50k_base    — text-davinci-002/003, code-davinci-002
#   r50k_base    — GPT-3 (davinci, curie, babbage, ada)
#
# Usage (run once on the host before starting the container):
#   chmod +x download-tiktoken-cache.sh
#   ./download-tiktoken-cache.sh
#
# The cache directory is mounted read-only into the container via run.sh.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="${TIKTOKEN_CACHE_DIR:-${SCRIPT_DIR}/../tiktoken_cache}"
CACHE_DIR="$(realpath -m "$CACHE_DIR")"

echo "Tiktoken cache directory: $CACHE_DIR"
mkdir -p "$CACHE_DIR"

# Confirm tiktoken is available
if ! python3 -c "import tiktoken" 2>/dev/null; then
  echo "tiktoken not found — installing..."
  pip3 install tiktoken --quiet
fi

# Download all encodings into the cache dir
TIKTOKEN_CACHE_DIR="$CACHE_DIR" python3 - <<'EOF'
import tiktoken, os

encodings = [
    ("cl100k_base",  "GPT-4, GPT-3.5-turbo, text-embedding-ada-002"),
    ("o200k_base",   "GPT-4o, GPT-4o-mini"),
    ("p50k_base",    "text-davinci-002/003, code-davinci-002"),
    ("r50k_base",    "GPT-3 (davinci, curie, babbage, ada)"),
]

cache_dir = os.environ["TIKTOKEN_CACHE_DIR"]
print(f"Saving to: {cache_dir}\n")

for name, models in encodings:
    print(f"  Downloading {name:<16}  ({models})")
    tiktoken.get_encoding(name)

print(f"\nDone. Cache contents:")
for f in sorted(os.listdir(cache_dir)):
    size = os.path.getsize(os.path.join(cache_dir, f))
    print(f"  {f}  ({size/1024:.0f} KB)")
EOF

echo ""
echo "Cache ready at: $CACHE_DIR"
echo "Set in your environment:"
echo "  export TIKTOKEN_CACHE_DIR=\"$CACHE_DIR\""
