#!/usr/bin/env python3
import fcntl, json, os, re, subprocess, sys, tempfile
from contextlib import contextmanager

CONFIG = os.environ.get("NIRI_CONFIG") or "/home/za/.config/niri/config.kdl"
RULES = os.environ.get("NIRI_RULES") or "/home/za/.config/niri/cfg/rules.kdl"
LOCK_FILE = os.environ.get("NIRI_LOCK") or "/tmp/niri-toggle.lock"
SHADOW_STATE_FILE = os.environ.get("NIRI_SHADOW_STATE") or "/tmp/niri-shadow.json"
OPACITY_STATE_FILE = os.environ.get("NIRI_OPACITY_STATE") or "/tmp/niri-blur-opacity.json"
NOCTALIA_SETTINGS = os.environ.get("NOCTALIA_SETTINGS") or "/home/za/.config/noctalia/settings.json"
COLORS_FILE = os.environ.get("NOCTALIA_COLORS") or "/home/za/.config/noctalia/colors.json"
KITTY_CONFIG = os.environ.get("KITTY_CONFIG") or "/home/za/.config/kitty/kitty.conf"


def atomic_write(path, content):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=os.path.basename(path) + ".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        try: os.unlink(tmp)
        except OSError: pass
        raise


@contextmanager
def locked():
    with open(LOCK_FILE, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(lock, fcntl.LOCK_UN)


def modify_config(transform, read_path=None, write_path=None):
    with locked():
        src = read_path or CONFIG
        dst = write_path or CONFIG
        c = open(src).read()
        c = transform(c)
        atomic_write(dst, c)
        if dst == CONFIG:
            subprocess.run(["niri", "msg", "action", "load-config-file"])


def _read_config():
    return open(CONFIG).read()


# ── Block helpers ──────────────────────────────────────────────────

def _find_layout_close(content):
    m = re.search(r'layout\s*\{', content)
    if not m: return None
    start, depth, i = m.end(), 1, m.end()
    while i < len(content) and depth > 0:
        if content[i] == '{': depth += 1
        elif content[i] == '}': depth -= 1
        i += 1
    return i - 1 if depth == 0 else None


def ensure_block(content, block_name, default_block):
    if re.search(rf'(?<!-){re.escape(block_name)}\s*{{', content):
        return content
    m = re.search(r'\nbinds\s*\{', content)
    pos = m.start() if m else len(content)
    return content[:pos] + '\n\n' + default_block + '\n' + content[pos:]


def ensure_in_layout(content, block_name, default_block):
    if re.search(rf'(?<!-){re.escape(block_name)}\s*{{', content):
        return content
    close = _find_layout_close(content)
    if close is not None:
        indented = '\n'.join('    ' + l if l.strip() else l for l in default_block.split('\n'))
        return content[:close] + '\n' + indented + '\n' + content[close:]
    return content + '\n\nlayout {\n' + default_block + '\n}\n'


def ensure_window_rule(content, prop, template):
    if re.search(rf'(?<!-){re.escape(prop)}', content):
        return content
    m = re.search(r'\nbinds\s*\{', content)
    pos = m.start() if m else len(content)
    return content[:pos] + '\n' + template + '\n' + content[pos:]


def ensure_background_effect(content):
    if re.search(r'(?<!-)(window-rule\s*\{[^}]*background-effect\s*\{)', content, re.DOTALL):
        return content
    rule = 'window-rule {\n    draw-border-with-background\n    background-effect {\n        blur true\n        xray true\n    }\n    open-maximized true\n}'
    m = re.search(r'\nbinds\s*\{', content)
    pos = m.start() if m else len(content)
    return content[:pos] + '\n' + rule + '\n' + content[pos:]


# ── On/off toggle helpers ──────────────────────────────────────────

def _toggle_onoff(block):
    if re.search(r'^\s*on\s*$', block, re.MULTILINE):
        return re.sub(r'^(\s*)on(\s*)$', r'\1off\2', block, count=1, flags=re.MULTILINE)
    if re.search(r'^\s*off\s*$', block, re.MULTILINE):
        return re.sub(r'^(\s*)off(\s*)$', r'\1on\2', block, count=1, flags=re.MULTILINE)
    return re.sub(r'^(\s*)(?:$|//)', r'\1on\n\1', block, count=1, flags=re.MULTILINE)


def _set_onoff(block, state):
    if re.search(r'^\s*(on|off)\s*$', block, re.MULTILINE):
        return re.sub(r'^\s*(on|off)\s*$', f'    {state}', block, count=1, flags=re.MULTILINE)
    return f'    {state}\n{block}'


# ── Corner radius ──────────────────────────────────────────────────

def set_corner_radius(config_val, rules_val):
    with locked():
        try:
            rc = open(RULES).read()
            if re.search(r'geometry-corner-radius\s+\d+', rc):
                rc = re.sub(r'(geometry-corner-radius )\d+', f'\\g<1>{rules_val}', rc)
            else:
                rc += f'\nwindow-rule {{\n    geometry-corner-radius {rules_val}\n    clip-to-geometry true\n}}\n'
            atomic_write(RULES, rc)
        except FileNotFoundError:
            pass

        try:
            c = open(CONFIG).read()
            def replace_corner(m):
                inner = re.sub(r'geometry-corner-radius \d+', f'geometry-corner-radius {config_val}', m.group(1))
                return f'window-rule {{{inner}}}'
            new_c = re.sub(r'(?<!/-)window-rule\s*\{([^}]*)\}', replace_corner, c, flags=re.DOTALL)
            if new_c == c:
                c = ensure_window_rule(c, 'geometry-corner-radius',
                    f'window-rule {{\n    geometry-corner-radius {config_val}\n    clip-to-geometry true\n}}')
            else:
                c = new_c
            atomic_write(CONFIG, c)
            subprocess.run(["niri", "msg", "action", "load-config-file"])
        except FileNotFoundError:
            pass


def corner_sync(radius_ratio_str):
    try: rr = float(radius_ratio_str)
    except: rr = 0.8
    set_corner_radius(0 if rr == 0.0 else 14, 0 if rr == 0.0 else 20)


# ── Blur ───────────────────────────────────────────────────────────

def set_niri_blur(value):
    onoff, bval = ("on", "true") if value == "true" else ("off", "false")
    def transform(c):
        c = ensure_background_effect(c)
        def rep(m):
            inner = m.group(1)
            if 'blur' in inner:
                return f'background-effect {{{inner.replace("blur true", f"blur {bval}").replace("blur false", f"blur {bval}")}}}'
            return f'background-effect {{\n        blur {bval}\n{inner}}}'
        c = re.sub(r'background-effect\s*\{([^}]*)\}', rep, c)
        c = ensure_in_layout(c, 'blur', f'blur {{\n    {onoff}\n}}')
        m = re.search(r'blur\s*\{([^}]*)\}', c)
        if m: c = c[:m.start()] + f'blur {{\n    {onoff}\n}}' + c[m.end():]
        return c
    modify_config(transform)


def set_blur_and_opacity(state):
    if state not in ("on", "off"): return
    bval = "true" if state == "on" else "false"
    opacity = "0.85" if state == "on" else "1.0"
    kitty_opacity = "0.5" if state == "on" else "1.0"

    def transform(c):
        c = ensure_in_layout(c, 'blur', f'blur {{\n    {state}\n}}')
        c = re.sub(r'blur\s*\{([^}]*)\}', f'blur {{\n    {state}\n}}', c)
        c = ensure_background_effect(c)
        def rep(m):
            inner = m.group(1)
            if 'blur' in inner:
                return f'background-effect {{{inner.replace("blur true", f"blur {bval}").replace("blur false", f"blur {bval}")}}}'
            return f'background-effect {{\n        blur {bval}\n{inner}}}'
        c = re.sub(r'background-effect\s*\{([^}]*)\}', rep, c)
        c = ensure_window_rule(c, 'open-maximized',
            f'window-rule {{\n    draw-border-with-background\n    opacity {opacity}\n    open-maximized true\n}}')
        lines = c.split('\n')
        for i, line in enumerate(lines):
            if 'open-maximized' in line:
                for j in range(i-1, max(0, i-10), -1):
                    if 'draw-border-with-background' in lines[j]:
                        if j+1 < len(lines) and 'opacity' in lines[j+1]:
                            lines[j+1] = f'    opacity {opacity}'
                        else:
                            lines.insert(j+1, f'    opacity {opacity}')
                        return '\n'.join(lines)
        return c

    modify_config(transform)

    try:
        kc = open(KITTY_CONFIG).read()
        if re.search(r'background_opacity\s+', kc):
            kc = re.sub(r'^(\s*background_opacity\s+)[0-9.]+', f'\\g<1>{kitty_opacity}', kc, flags=re.MULTILINE)
        else:
            kc += f'\nbackground_opacity {kitty_opacity}\n'
        atomic_write(KITTY_CONFIG, kc)
        subprocess.run(["pkill", "-SIGUSR1", "-x", "kitty"])
    except FileNotFoundError:
        pass


def toggle_global_blur():
    def transform(c):
        c = ensure_in_layout(c, 'blur', 'blur {\n    on\n}')
        m = re.search(r'blur\s*\{([^}]*)\}', c, re.DOTALL)
        if not m: return c + '\n\nblur {\n    on\n}\n'
        block = m.group(1)
        found = None
        extras = [l for l in block.split('\n') if l.strip() and not re.search(r'^\s*(on|off)\s*$', l)]
        for line in block.split('\n'):
            if re.search(r'^\s*on\s*$', line): found = True; break
            if re.search(r'^\s*off\s*$', line): found = False; break
        if found:
            opacities = re.findall(r'opacity\s+([0-9.]+)', c)
            atomic_write(OPACITY_STATE_FILE, json.dumps(opacities))
            c = re.sub(r'opacity\s+[0-9.]+', 'opacity 1.0', c)
            new_state = "off"
        else:
            try:
                saved = json.loads(open(OPACITY_STATE_FILE).read())
                def restore(m2): return f'opacity {saved.pop(0)}'
                c = re.sub(r'opacity\s+[0-9.]+', restore, c)
            except: pass
            new_state = "on"
        new_block = '\n    ' + new_state + '\n'
        if extras: new_block += '\n'.join(extras) + '\n'
        m2 = re.search(r'blur\s*\{([^}]*)\}', c, re.DOTALL)
        if m2: c = c[:m2.start()] + 'blur {' + new_block + '}' + c[m2.end():]
        return c
    modify_config(transform)


def toggle_window_blur():
    def transform(c):
        c = ensure_background_effect(c)
        def toggle(m):
            inner = m.group(1)
            if re.search(r'blur\s+true', inner):
                inner = re.sub(r'\s*blur\s+true\n?', '\n', inner)
                inner = re.sub(r'xray\s+true', 'xray false', inner)
                return f'background-effect {{{inner}}}'
            inner = re.sub(r'\s*blur\s+(true|false)\n?', '\n', inner)
            inner = re.sub(r'xray\s+false', 'xray true', inner)
            return f'background-effect {{\n        blur true\n{inner}}}'
        return re.sub(r'background-effect\s*\{([^}]*)\}', toggle, c)
    modify_config(transform)


def toggle_noise_saturation():
    def transform(c):
        c = ensure_in_layout(c, 'blur', 'blur {\n    on\n}')
        noise_m = re.search(r'noise\s+([0-9.]+)', c)
        new_noise = "0.15" if (float(noise_m.group(1)) if noise_m else 0.0) == 0.0 else "0"
        if re.search(r'noise\s+', c):
            c = re.sub(r'noise\s+[0-9.]+', f'noise {new_noise}', c)
        else:
            c = re.sub(r'(blur\s*\{\s*\n\s*(?:on|off)\s*\n)', f'\\1    noise {new_noise}\n\n', c)
        if re.search(r'saturation\s+', c):
            c = re.sub(r'saturation\s+[0-9.]+', 'saturation 1', c)
        else:
            c = re.sub(r'(noise\s+[0-9.]+\s*\n)', f'\\1    saturation 1\n\n', c)
        return c
    modify_config(transform)


# ── Focus ring ─────────────────────────────────────────────────────

def toggle_focus_ring():
    def transform(c):
        return re.sub(r'focus-ring\s*\{([^}]*)\}',
            lambda m: 'focus-ring {' + _toggle_onoff(m.group(1)) + '}', c, flags=re.DOTALL)
    modify_config(transform)


def set_focus_ring(state):
    if state not in ("on", "off"): return
    def transform(c):
        return re.sub(r'focus-ring\s*\{([^}]*)\}',
            lambda m: 'focus-ring {' + _set_onoff(m.group(1), state) + '}', c, flags=re.DOTALL)
    modify_config(transform)


def set_focus_ring_width(width):
    if width not in (1, 2, 3, 4, 5): return
    def transform(c):
        if re.search(r'width\s+\d+', c):
            return re.sub(r'width\s+\d+', f'width {width}', c)
        return re.sub(r'(focus-ring\s*\{)', rf'\1\n        width {width}', c)
    modify_config(transform)


def get_focus_ring_width():
    try:
        m = re.search(r'width\s+(\d+)', _read_config())
        print(m.group(1) if m else "3")
    except Exception: print("3")


def get_focus_ring_gradient_state():
    try:
        print("on" if re.search(r'active-gradient\s+from=', _read_config()) else "off")
    except Exception: print("off")


def set_focus_ring_gradient(state):
    if state not in ("on", "off"): return
    gradient_line = '        active-gradient from="#ff0080" to="#00d4ff" angle=45 relative-to="workspace-view"\n'

    def add_gradient(m):
        block = m.group(0)
        if 'active-gradient' in block:
            return re.sub(r'active-gradient[^\n]*\n?', gradient_line, block)
        return re.sub(r'(active-color\s+"#[0-9a-fA-F]+"\n)', r'\1' + gradient_line, block, count=1)

    def remove_gradient(m):
        block = re.sub(r'\n?\s*active-gradient[^\n]*', '', m.group(0))
        try: primary = json.load(open(COLORS_FILE)).get("mPrimary", "#67abe4")
        except: primary = "#67abe4"
        return re.sub(r'(active-color\s+")#[^"\n]+(")', rf'\g<1>{primary}\g<2>', block)

    def transform(c):
        return re.sub(r'focus-ring \{[^}]*\}', add_gradient if state == "on" else remove_gradient, c, flags=re.DOTALL)
    modify_config(transform)


def sync_focus_ring_color():
    try:
        try: primary = json.load(open(COLORS_FILE)).get("mPrimary", "#67abe4")
        except: primary = "#67abe4"

        def transform(c):
            return re.sub(r'focus-ring \{[^}]*\}',
                lambda m: re.sub(r'(active-color\s+")#[^"\n]+(")', rf'\g<1>{primary}\g<2>', m.group(0)),
                c, flags=re.DOTALL)
        modify_config(transform)
    except Exception as e:
        print(f"sync-focus-ring-color failed: {e}", file=sys.stderr)


# ── Shadow ──────────────────────────────────────────────────────────

def get_shadow_state():
    try:
        m = re.search(r'shadow\s*\{([^}]*)\}', _read_config(), re.DOTALL)
        if m: return "on" if re.search(r'^\s*on\s*$', m.group(1), re.MULTILINE) else "off"
    except: pass
    return "off"


def _parse_shadow_block(raw=None):
    try:
        c = raw or _read_config()
    except: return None
    m = re.search(r'shadow\s*\{([^}]*)\}', c, re.DOTALL)
    if not m: return None
    inner = m.group(1)
    def g(pat, default, cast=str):
        x = re.search(pat, inner)
        return cast(x.group(1)) if x else default
    return {
        "on": re.search(r'^\s*on\s*$', inner, re.MULTILINE) is not None,
        "color": g(r'color\s+"([^"]+)"', "#000000"),
        "softness": g(r'softness\s+(\d+)', 6, int),
        "spread": g(r'spread\s+(\d+)', 0, int),
        "offsetX": g(r'offset-x\s+(-?\d+)', g(r'(?<!y=)x=(-?\d+)', 0, int), int),
        "offsetY": g(r'offset-y\s+(-?\d+)', g(r'y=(-?\d+)', 4, int), int),
    }


def _default_shadow_props():
    return {"on": False, "color": "#000000", "softness": 6, "spread": 0, "offsetX": 0, "offsetY": 4}


def write_shadow_props():
    props = _parse_shadow_block() or _default_shadow_props()
    atomic_write(SHADOW_STATE_FILE, json.dumps(props))
    write_shadow_to_settings(props)
    print(json.dumps(props))


def get_shadow_props():
    print(json.dumps(_parse_shadow_block() or _default_shadow_props()))


def write_shadow_to_settings(props):
    try: settings = json.load(open(NOCTALIA_SETTINGS))
    except: settings = {}
    settings.setdefault("bar", {}).update(
        shadowEnabled=props["on"], shadowColor=props["color"],
        shadowSoftness=props["softness"], shadowSpread=props["spread"],
        shadowOffsetX=props["offsetX"], shadowOffsetY=props["offsetY"])
    atomic_write(NOCTALIA_SETTINGS, json.dumps(settings, indent=4))


def sync_shadow_to_focus_ring():
    def transform(c):
        m = re.search(r'focus-ring\s*\{[^}]*active-color\s+"([^"]+)"', c, re.DOTALL)
        if not m: return c
        return re.sub(r'shadow\s*\{[^}]*\}',
            lambda m2: re.sub(r'color\s+"[^"]*"', f'color "{m.group(1)}"', m2.group(0)), c, flags=re.DOTALL)
    modify_config(transform)
    write_shadow_props()


def toggle_shadow():
    def transform(c):
        c = ensure_in_layout(c, 'shadow', 'shadow {\n    on\n    softness 30\n    spread 5\n    offset x=0 y=5\n    color "#0007"\n}')
        m = re.search(r'shadow\s*\{([^}]*)\}', c, re.DOTALL)
        if m: c = c[:m.start()] + 'shadow {' + _toggle_onoff(m.group(1)) + '}' + c[m.end():]
        return c
    modify_config(transform)


# ── Kitty opacity ──────────────────────────────────────────────────

def set_kitty_opacity(value):
    try:
        kc = open(KITTY_CONFIG).read()
        if re.search(r'background_opacity\s+', kc):
            kc = re.sub(r'^(\s*background_opacity\s+)[0-9.]+', f'\\g<1>{value}', kc, flags=re.MULTILINE)
        else:
            kc += f'\nbackground_opacity {value}\n'
        atomic_write(KITTY_CONFIG, kc)
        subprocess.run(["pkill", "-SIGUSR1", "-x", "kitty"])
        return True
    except FileNotFoundError: return False


def cycle_kitty_opacity():
    try:
        m = re.search(r'background_opacity\s+([0-9.]+)', open(KITTY_CONFIG).read())
        current = float(m.group(1)) if m else 1.0
        set_kitty_opacity("0.0" if current >= 1.0 else ("0.5" if current >= 0.25 else "1.0"))
    except FileNotFoundError: pass


# ── Main ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time as _t
    try:
        with open("/tmp/niri-toggle-calls.log", "a") as lf:
            lf.write(f"[{_t.strftime('%H:%M:%S')}] PID={os.getpid()} PPID={os.getppid()} CMD={' '.join(sys.argv)}\n")
    except: pass

    def usage():
        print("usage: niri-toggle.py {square|round|focus-ring|set-focus-ring <on|off>|focus-ring-gradient <on|off>|get-focus-ring-gradient|focus-ring-width <1-5>|get-focus-ring-width|blur-off|blur-on|blur-global-toggle|blur-window-toggle|noise-toggle|glass-cycle|glass-set <opacity>|shadow-toggle|shadow-sync|shadow-get|sync-focus-ring-color|corner-sync <ratio>}")
        sys.exit(1)

    if len(sys.argv) < 2: usage()
    cmd = sys.argv[1]

    arg1 = lambda: sys.argv[2] if len(sys.argv) > 2 else usage()
    cmds = {
        "square": lambda: set_corner_radius(0, 0),
        "round": lambda: set_corner_radius(14, 20),
        "focus-ring": toggle_focus_ring,
        "set-focus-ring": lambda: set_focus_ring(arg1()),
        "focus-ring-gradient": lambda: set_focus_ring_gradient(arg1()),
        "get-focus-ring-gradient": get_focus_ring_gradient_state,
        "focus-ring-width": lambda: set_focus_ring_width(int(arg1())),
        "get-focus-ring-width": get_focus_ring_width,
        "blur-off": lambda: set_blur_and_opacity("off"),
        "blur-on": lambda: set_blur_and_opacity("on"),
        "noise-toggle": toggle_noise_saturation,
        "blur-global-toggle": toggle_global_blur,
        "blur-window-toggle": toggle_window_blur,
        "glass-cycle": cycle_kitty_opacity,
        "glass-set": lambda: set_kitty_opacity(arg1()),
        "corner-sync": lambda: corner_sync(arg1()),
        "shadow-toggle": toggle_shadow,
        "shadow-sync": sync_shadow_to_focus_ring,
        "shadow-get": get_shadow_props,
        "sync-focus-ring-color": sync_focus_ring_color,
    }
    fn = cmds.get(cmd)
    if fn: fn()
    else: print(f"unknown: {cmd}"); sys.exit(1)
