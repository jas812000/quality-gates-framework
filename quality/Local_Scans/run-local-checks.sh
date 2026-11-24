#!/bin/sh
set -eu
REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$REPO_ROOT"
# Python manages Downloads/quality-gates-reports/ and QUALITY_OUTPUT_DIR.
if command -v python3 >/dev/null 2>&1; then
    exec python3 -m quality.Local_Scans.run_local_checks "$@"
fi
exec python -m quality.Local_Scans.run_local_checks "$@"
