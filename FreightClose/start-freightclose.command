#!/bin/sh
# macOS/Linux launcher: double-click in Finder, or run ./start-freightclose.command [--fresh]
cd "$(dirname "$0")" || exit 1
for py in python3.13 python3.12 python3.11 python3; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    exec "$py" offline_server.py --port 0 --open-browser "$@"
  fi
done
echo "Install Python 3.11 or later, then run this launcher again."
read -r _
