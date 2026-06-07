#!/usr/bin/env bash
# Load test redirects with hey (https://github.com/rakyll/hey)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
DURATION="${DURATION:-30s}"
CONCURRENCY="${CONCURRENCY:-50}"
OUTPUT_DIR="${OUTPUT_DIR:-results}"
CODE="${CODE:-}"

mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_FILE="$OUTPUT_DIR/hey_${TIMESTAMP}.txt"

if [ -z "$CODE" ]; then
  echo "Creating a short URL for load test..."
  CREATE_PAYLOAD='{"long_url":"https://example.com/hey-load-test"}'
  CODE=$(curl -sf -X POST "$BASE_URL/shorten" \
    -H "Content-Type: application/json" \
    -d "$CREATE_PAYLOAD" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["short_code"])')
fi

TARGET="$BASE_URL/$CODE"

echo "=== hey redirect load test ===" | tee "$OUT_FILE"
echo "Target: $TARGET" | tee -a "$OUT_FILE"
echo "Duration: $DURATION, Concurrency: $CONCURRENCY" | tee -a "$OUT_FILE"
echo "" | tee -a "$OUT_FILE"

if ! command -v hey &> /dev/null; then
  echo "ERROR: 'hey' not found. Install: brew install hey" | tee -a "$OUT_FILE"
  exit 1
fi

hey -z "$DURATION" -c "$CONCURRENCY" "$TARGET" 2>&1 | tee -a "$OUT_FILE"

echo "" | tee -a "$OUT_FILE"
echo "=== Application metrics (after load) ===" | tee -a "$OUT_FILE"
curl -s "$BASE_URL/metrics" | tee -a "$OUT_FILE"
echo "" | tee -a "$OUT_FILE"
echo "Results saved to $OUT_FILE"
echo "Copy latency percentiles and cache_hit_rate into results/metrics_template.md"
