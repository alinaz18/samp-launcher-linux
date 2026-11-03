#!/usr/bin/env bash
# Lay out the launcher files for a system-wide package (deb / rpm / PKGBUILD).
#   packaging/stage.sh <destdir> [prefix=/usr]
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:?destdir required}"
PREFIX="${2:-/usr}"

install -Dm644 "$SRC/samp_launcher.py"           "$DEST$PREFIX/share/samp-launcher/samp_launcher.py"
install -Dm644 "$SRC/data/samp-launcher.svg"     "$DEST$PREFIX/share/icons/hicolor/scalable/apps/samp-launcher.svg"
install -Dm644 "$SRC/LICENSE"                    "$DEST$PREFIX/share/licenses/samp-launcher/LICENSE"
install -Dm644 "$SRC/README.md"                  "$DEST$PREFIX/share/doc/samp-launcher/README.md"
install -Dm644 "$SRC/README.en.md"               "$DEST$PREFIX/share/doc/samp-launcher/README.en.md"

install -dm755 "$DEST$PREFIX/bin" "$DEST$PREFIX/share/applications"
cat > "$DEST$PREFIX/bin/samp-launcher" <<EOF
#!/bin/sh
exec python3 $PREFIX/share/samp-launcher/samp_launcher.py "\$@"
EOF
chmod 755 "$DEST$PREFIX/bin/samp-launcher"
sed "s|@BIN@|samp-launcher|" "$SRC/data/samp-launcher.desktop" > "$DEST$PREFIX/share/applications/samp-launcher.desktop"
chmod 644 "$DEST$PREFIX/share/applications/samp-launcher.desktop"
