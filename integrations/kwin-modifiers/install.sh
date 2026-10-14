#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
cast_effect_dir="$HOME/.local/share/kwin/effects/desktopcast-modifiers"
mkdir -p "$cast_effect_dir"
cp -r package/. "$cast_effect_dir/"
# Replace the inode atomically, avoiding modification of a mapped library.
cp build/libdesktopcast_modifier_bridge.so "$cast_effect_dir/contents/ui/bridge/.bridge-new.so"
mv "$cast_effect_dir/contents/ui/bridge/.bridge-new.so" "$cast_effect_dir/contents/ui/bridge/libdesktopcast_modifier_bridge.so"
cp build/kwin-version.txt "$cast_effect_dir/kwin-version.txt"
printf '%s\n' 'Installed the user-local helper. Reopen Desktop Cast to use it.'
