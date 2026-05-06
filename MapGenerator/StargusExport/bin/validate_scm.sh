#!/bin/bash
set -euo pipefail

MIN_SCM_BYTES="${MIN_SCM_BYTES:-10240}"

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path-to-map.scm>"
    exit 2
fi

SCM_PATH="$1"
if [ ! -f "$SCM_PATH" ]; then
    echo "[SCM] Missing file: $SCM_PATH"
    exit 1
fi

SCM_SIZE=$(stat -c '%s' "$SCM_PATH" 2>/dev/null || echo 0)
if [ "$SCM_SIZE" -lt "$MIN_SCM_BYTES" ]; then
    echo "[SCM] Too small: $SCM_SIZE bytes (min $MIN_SCM_BYTES)"
    exit 1
fi

SCM_SIG=$(dd if="$SCM_PATH" bs=4 count=1 2>/dev/null | od -An -t x1 | tr -d ' \n')
if [ "$SCM_SIG" != "4d50511a" ]; then
    echo "[SCM] Bad header: $SCM_SIG (expected 4d50511a)"
    exit 1
fi

VALIDATE_PY="$(dirname "$0")/validate_scm.py"
if [ -x "$VALIDATE_PY" ]; then
    if ! "$VALIDATE_PY" "$SCM_PATH"; then
        exit 1
    fi
else
    echo "[SCM] Warning: validate_scm.py missing; cannot verify staredit\\scenario.chk"
fi

echo "[SCM] OK: $SCM_PATH ($SCM_SIZE bytes, MPQ header OK)"
