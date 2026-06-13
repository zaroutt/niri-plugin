
# niri-plugin
<img width="352" height="184" alt="Screenshot from 2026-06-13 11-57-08" src="https://github.com/user-attachments/assets/7ae9f7af-5d8c-4fff-a85d-5fc067c6e36b" />

A plugin for [noctalia-shell](https://github.com/noctalia-dev/noctalia) that adds a panel and bar controls for the [niri](https://github.com/YaLTeR/niri) Wayland compositor.

## Features

- Toggle niri focus ring on/off
- Toggle niri shadow on/off  
- Toggle global blur (affects all window backgrounds)
- Toggle per-window background blur (blur/xray)
- Set blur on/off with opacity presets
- Toggle noise/saturation for the blur effect
- Change focus ring width (1–5)
- Enable/disable focus ring gradient
- Sync focus ring color to noctalia theme
- Sync shadow color to focus ring color
- Set window corner radius (round / square)
- Adjust kitty terminal opacity
- All changes apply live via `niri msg action load-config-file`

## Installation

### Using install.sh (recommended)

Clone the repository and run the install script:

```sh
git clone <repo-url>
cd tentativa
./install.sh
```

The script will:

1. Copy all noctalia configuration files to `~/.config/noctalia/`
2. Copy the noctalia-shell files to `/etc/xdg/quickshell/noctalia-shell/` (requires sudo)
3. Copy this niri-plugin to `~/.config/noctalia/plugins/niri-config/`
4. Enable `niri-config` in `~/.config/noctalia/plugins.json`
5. Restart the shell with `pkill qs`

### Manual installation

```sh
# Copy plugin files
mkdir -p ~/.config/noctalia/plugins/niri-config/scripts
cp niri-plugin/manifest.json ~/.config/noctalia/plugins/niri-config/
cp niri-plugin/Panel.qml ~/.config/noctalia/plugins/niri-config/
cp niri-plugin/BarWidget.qml ~/.config/noctalia/plugins/niri-config/
cp niri-plugin/settings.json ~/.config/noctalia/plugins/niri-config/
cp niri-plugin/niri-toggle.py ~/.config/noctalia/plugins/niri-config/scripts/

# Enable the plugin
# Add "niri-config": { "enabled": true } to ~/.config/noctalia/plugins.json

# Restart noctalia-shell
pkill qs
```

## Usage

After installation:

1. Open the Settings panel in noctalia-shell
2. Go to **Bar** > **Widgets**
3. Add `plugin:niri-config` to your bar
4. The plugin adds an icon to your bar that opens the niri controls panel
5. Click the button in the panel to toggle settings

## Notes

- The script creates any missing config blocks (`blur`, `shadow`, `background-effect`, etc.) automatically if they don't exist in your niri config
- Paths can be overridden via environment variables: `NIRI_CONFIG`, `NIRI_RULES`, `NIRI_LOCK`, etc.
- Changes are applied live — no niri restart needed
