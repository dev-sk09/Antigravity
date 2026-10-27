#!/usr/bin/env bash
# run_all.sh - offline tests for the Local Agent sidecar (no network, no keys).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
fail=0
for t in test_agent.py test_tools.py; do
    echo "--> Running $t..."
    if ! python3 -I "$HERE/$t" 2>&1 | tail -4; then
        fail=1
    fi
done
[ "$fail" -eq 0 ] && echo "=== ALL LOCAL AGENT TESTS PASSED ===" || { echo "=== LOCAL AGENT TESTS FAILED ==="; exit 1; }
