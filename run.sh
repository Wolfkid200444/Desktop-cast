#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
unset PYTHONPATH PYTHONHOME
export QT_QPA_PLATFORM=wayland
exec "${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/}python3" app.py "$@"
