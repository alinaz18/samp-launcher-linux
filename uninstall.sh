#!/usr/bin/env bash
# SA-MP Launcher — uninstall / удаление
#   ./uninstall.sh          remove the launcher, keep settings and the Wine prefix
#   ./uninstall.sh --purge  also remove settings, favorites and the Wine prefix
#                           (your GTA San Andreas folder is never touched)
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

rm -rf "$DATA/samp-launcher-app"
rm -f "$HOME/.local/bin/samp-launcher" \
      "$DATA/applications/samp-launcher.desktop" \
      "$DATA/icons/hicolor/scalable/apps/samp-launcher.svg" \
      "$DATA"/icons/hicolor/*/apps/samp-launcher-original.png \
      "$DATA/samp-launcher/icon-source"
update-desktop-database "$DATA/applications" 2>/dev/null || true

if [ "${1:-}" = "--purge" ]; then
  rm -rf "$DATA/samp-launcher" "$CONF/samp-launcher"
  echo "Removed launcher, settings and Wine prefix. / Лаунчер, настройки и окружение Wine удалены."
else
  echo "Launcher removed. Settings: $CONF/samp-launcher, Wine prefix: $DATA/samp-launcher"
  echo "Лаунчер удалён. Настройки и окружение Wine оставлены (удалить: ./uninstall.sh --purge)."
fi
