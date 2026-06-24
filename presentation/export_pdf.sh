#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/dist"
OUTPUT_FILE="${1:-$OUTPUT_DIR/tp5_presentation.pdf}"
CHROME="${CHROME:-google-chrome}"

mkdir -p "$OUTPUT_DIR"

"$CHROME" \
  --headless=new \
  --no-sandbox \
  --disable-gpu \
  --print-to-pdf="$OUTPUT_FILE" \
  --print-to-pdf-no-header \
  "file://$SCRIPT_DIR/index.html?print=1"

echo "Presentation exported to: $OUTPUT_FILE"
