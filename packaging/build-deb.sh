#!/usr/bin/env bash
# Build dist/samp-launcher_<version>_all.deb (needs dpkg-deb).
#   packaging/build-deb.sh <version>
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VER="${1:?version required}"
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT

"$SRC/packaging/stage.sh" "$ROOT"
# Debian keeps the license in /usr/share/doc/<pkg>/copyright
mv "$ROOT/usr/share/licenses/samp-launcher/LICENSE" "$ROOT/usr/share/doc/samp-launcher/copyright"
rm -rf "$ROOT/usr/share/licenses"

mkdir -p "$ROOT/DEBIAN"
cat > "$ROOT/DEBIAN/control" <<EOF
Package: samp-launcher
Version: $VER
Section: games
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-pyside6.qtcore, python3-pyside6.qtgui, python3-pyside6.qtwidgets, wine
Recommends: winetricks, wine32
Maintainer: bagira818 <noreply@github.com>
Homepage: https://github.com/alinaz18/samp-launcher-linux
Description: SA-MP launcher for Linux
 Native Qt launcher for SA-MP (GTA San Andreas multiplayer): server
 browser, favorites, nickname and a configurable game folder for mods.
 The Windows game itself runs through a Wine prefix managed by the launcher.
EOF
cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
EOF
chmod 755 "$ROOT/DEBIAN/postinst"

mkdir -p "$SRC/dist"
dpkg-deb --root-owner-group --build "$ROOT" "$SRC/dist/samp-launcher_${VER}_all.deb"
