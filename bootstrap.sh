#!/usr/bin/env bash
# Reflection Lab bootstrap for Linux and macOS: creates .venv, installs the packages, runs the
# environment check. Safe to run again.
#
#   ./bootstrap.sh            normal
#   ./bootstrap.sh --with-cli also install the litert-lm command-line tool (optional fallback runtime)
set -euo pipefail
cd "$(dirname "$0")"

PY=""
for v in python3.12 python3.11 python3.13 python3; do
  if command -v "$v" >/dev/null 2>&1 && "$v" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    PY="$v"; break
  fi
done
[ -z "$PY" ] && { echo "Python 3.11+ not found. Install it with your package manager."; exit 1; }
echo ">> using $($PY --version)"

[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
if [ "${1:-}" = "--with-cli" ]; then .venv/bin/python -m pip install litert-lm || echo "litert-lm CLI install failed (optional)"; fi
.venv/bin/python scripts/check_env.py --probe-api
echo
echo "Done. Activate the environment with: source .venv/bin/activate"
