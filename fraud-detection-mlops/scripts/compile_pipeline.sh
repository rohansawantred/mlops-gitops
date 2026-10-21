#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
python3 -m pipelines.fraud_pipeline
echo "Pipeline YAML at pipelines/fraud_detection_pipeline.yaml (after compile)"
