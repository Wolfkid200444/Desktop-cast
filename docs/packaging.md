# Linux packages

The workflow tests each push and builds x86_64 AppImage, Debian, RPM and a portable
archive on Ubuntu 24.04. Tags named vVERSION publish the artifacts and SHA256SUMS
to GitHub Releases. Update VERSION and CHANGELOG.md before tagging.

These packages bundle Python, PySide6 and Pillow. They require a host Quickshell
installation, KDE Plasma Wayland, and glibc 2.39 or newer. They are not universal
Linux binaries and do not include the KWin helper or Steam runtime. Debian/RPM
packages declare a quickshell dependency; your distribution may require an extra
repository for it. FFmpeg is optional for video conversion.

The KWin modifier helper must be built on the target machine against exactly the
installed KWin version. See ../integrations/kwin-modifiers/install.sh. Rebuild after a KWin
upgrade. The app otherwise remains usable through the library Controls button.

Flatpak is not shipped in 0.2.0. Its sandbox cannot directly reuse the host
Quickshell executable and Steam library in the current architecture. A supported
Flatpak needs a bundled overlay and a separate, narrowly scoped host integration
for Steam/KWin. A manifest alone would not make those functions work.

Local build: install requirements-build.txt, fpm 1.16.0, rpm, squashfs-tools and
appimagetool 1.9.1, then run packaging/build.sh. Output is in artifacts/.
