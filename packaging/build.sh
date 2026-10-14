#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
version=$(cat VERSION)
mkdir -p artifacts
python -m PyInstaller --noconfirm --clean --name desktop-cast \
  --add-data 'Character.qml:.' --add-data 'ControlPanel.qml:.' --add-data 'shell.qml:.' \
  --add-data 'theme.qss:.' --add-data 'VERSION:.' --add-data 'packaging/desktop-cast.svg:.' \
  --hidden-import steam_download app.py
mkdir -p build/AppDir/usr/bin build/AppDir/usr/share/applications build/AppDir/usr/share/icons/hicolor/scalable/apps
cp -a dist/desktop-cast/. build/AppDir/usr/bin/
cp packaging/desktop-cast.desktop build/AppDir/
cp packaging/desktop-cast.svg build/AppDir/
cp packaging/desktop-cast.desktop build/AppDir/usr/share/applications/
cp packaging/desktop-cast.svg build/AppDir/usr/share/icons/hicolor/scalable/apps/
cat > build/AppDir/AppRun <<'RUN'
#!/bin/sh
cast_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
unset PYTHONPATH PYTHONHOME
export QT_QPA_PLATFORM=wayland
exec "$cast_dir/usr/bin/desktop-cast" "$@"
RUN
chmod +x build/AppDir/AppRun
QT_QPA_PLATFORM=offscreen dist/desktop-cast/desktop-cast --version
ARCH=x86_64 appimagetool --appimage-extract-and-run build/AppDir "artifacts/Desktop-Cast-${version}-x86_64.AppImage"
mkdir -p build/native/opt/desktop-cast build/native/usr/bin build/native/usr/share/applications build/native/usr/share/icons/hicolor/scalable/apps
cp -a dist/desktop-cast/. build/native/opt/desktop-cast/
cat > build/native/usr/bin/desktop-cast <<'RUN'
#!/bin/sh
unset PYTHONPATH PYTHONHOME
export QT_QPA_PLATFORM=wayland
exec /opt/desktop-cast/desktop-cast "$@"
RUN
chmod +x build/native/usr/bin/desktop-cast
cp packaging/desktop-cast.desktop build/native/usr/share/applications/
cp packaging/desktop-cast.svg build/native/usr/share/icons/hicolor/scalable/apps/
for format in deb rpm; do
  fpm -s dir -t "$format" -n desktop-cast -v "$version" --iteration 1 \
    --architecture x86_64 --license GPL-3.0-or-later \
    --maintainer 'Desktop Cast contributors' \
    --description 'Wayland desktop animation player. Requires host Quickshell and KDE Plasma Wayland.' \
    --url https://github.com/Wolfkid200444/Desktop-cast \
    --depends quickshell -C build/native -p artifacts/ .
done
tar -czf "artifacts/Desktop-Cast-${version}-linux-x86_64.tar.gz" -C dist desktop-cast
(cd artifacts && sha256sum * > SHA256SUMS)
