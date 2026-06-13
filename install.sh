#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing niri-config plugin ==="
PLUGIN_DIR="$HOME/.config/noctalia/plugins/niri-config"
mkdir -p "$PLUGIN_DIR/scripts"

cp -rv "$SCRIPT_DIR/manifest.json" "$PLUGIN_DIR/"
cp -rv "$SCRIPT_DIR/Panel.qml" "$PLUGIN_DIR/"
cp -rv "$SCRIPT_DIR/BarWidget.qml" "$PLUGIN_DIR/"
cp -rv "$SCRIPT_DIR/settings.json" "$PLUGIN_DIR/"
cp -rv "$SCRIPT_DIR/scripts/niri-toggle.py" "$PLUGIN_DIR/scripts/"

echo ""
echo "=== Enabling plugin in plugins.json ==="
PLUGINS_JSON="$HOME/.config/noctalia/plugins.json"
if ! grep -q '"niri-config"' "$PLUGINS_JSON" 2>/dev/null; then
  sed -i 's/"todo": {/"niri-config": {\n            "enabled": true\n        },\n        "todo": {/' "$PLUGINS_JSON"
  echo "niri-config enabled"
else
  echo "niri-config already enabled"
fi

echo ""
echo "=== Done ==="
echo "Add plugin:niri-config to your bar widgets in Settings > Bar > Widgets"
echo "Restart noctalia-shell: pkill qs"
