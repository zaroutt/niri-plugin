import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Widgets
import qs.Services.UI
import qs.Services.Theming

Item {
  id: root
  property var pluginApi: null
  readonly property var geometryPlaceholder: panelContainer
  readonly property bool allowAttach: true
  property real contentPreferredWidth: 360 * Style.uiScaleRatio
  property real contentPreferredHeight: mainCol.implicitHeight + Style.marginM * 2
  anchors.fill: parent
  property bool squareCorners: false
  property bool noiseEnabled: false
  property bool focusRingEnabled: false
  property bool focusRingGradient: true
  property int focusRingWidth: 3

  function refreshFocusRingState() {
    if (_niriBusy) return
    _niriBusy = true
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "get-focus-ring-gradient"] })
  }

  property int kittyGlassMode: 0
  property bool niriBlurGlobalEnabled: false
  property bool niriBlurWindowEnabled: false
  property bool _niriBusy: false

  Timer {
    id: niriBusyTimeout
    interval: 5000
    repeat: false
    onTriggered: {
      if (root._niriBusy) {
        root._niriBusy = false
        Logger.w("NiriConfig", "niriBusy timeout - reset")
      }
    }
  }

  readonly property string _scriptsDir: Qt.resolvedUrl("scripts/").toString().replace("file://", "")

  Process {
    id: niriProc
    stdout: StdioCollector {}
    stderr: StdioCollector {}
    onExited: function(exitCode, exitStatus) {
      root._niriBusy = false
      if (exitCode !== 0) {
        Logger.w("NiriConfig", "niri-toggle failed: " + stderr.text)
      } else {
        var text = stdout.text.trim()
        if (text === "on" || text === "off") {
          root.focusRingGradient = (text === "on")
          if (!root._niriBusy && !niriProc.running) {
            root._niriBusy = true
            niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "get-focus-ring-width"] })
          }
        } else if (/^\d+$/.test(text)) {
          var w = parseInt(text)
          if (w > 0 && w <= 10) root.focusRingWidth = w
        } else if (text !== "") {
          root.applyNiriShadowState(text)
        }
      }
    }
  }

  Process {
    id: deferredProc
    stdout: StdioCollector {}
    stderr: StdioCollector {}
    onExited: function(exitCode, exitStatus) {
      if (exitCode !== 0)
        Logger.w("NiriConfig", "deferred toggle failed: " + stderr.text)
    }
  }

  Component.onCompleted: refreshFocusRingState()

  function applyNiriShadowState(jsonText) {
    try {
      var p = JSON.parse(jsonText)
      if (p.on === undefined) return
      if (p.on !== undefined)      Settings.data.bar.shadowEnabled  = p.on
      if (p.color)                 Settings.data.bar.shadowColor    = p.color
      if (p.softness !== undefined) Settings.data.bar.shadowSoftness = p.softness
      if (p.spread !== undefined)  Settings.data.bar.shadowSpread   = p.spread
      if (p.offsetX !== undefined) Settings.data.bar.shadowOffsetX  = p.offsetX
      if (p.offsetY !== undefined) Settings.data.bar.shadowOffsetY  = p.offsetY
      Settings.saveImmediate()
    } catch(e) {}
  }

  function toggleSquareCorners() {
    if (_niriBusy) return
    if (squareCorners) {
      Settings.data.general.radiusRatio  = 0.8
      Settings.data.general.iRadiusRatio = 0.8
      _niriBusy = true
      niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "round"] })
      squareCorners = false
    } else {
      Settings.data.general.radiusRatio  = 0
      Settings.data.general.iRadiusRatio = 0
      _niriBusy = true
      niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "square"] })
      squareCorners = true
    }
  }

  function toggleFocusRing() {
    if (_niriBusy) return
    _niriBusy = true
    focusRingEnabled = !focusRingEnabled
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "focus-ring"] })
  }

  function toggleFocusRingGradient() {
    if (_niriBusy) return
    _niriBusy = true
    focusRingGradient = !focusRingGradient
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "focus-ring-gradient", focusRingGradient ? "on" : "off"] })
  }

  function toggleFocusRingWidth() {
    if (_niriBusy) return
    _niriBusy = true
    var widths = [1, 2, 3, 4, 5]
    var idx = widths.indexOf(focusRingWidth)
    var next = (idx + 1) % widths.length
    focusRingWidth = widths[next]
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "focus-ring-width", String(focusRingWidth)] })
  }

  function toggleNoiseSat() {
    if (_niriBusy) return
    _niriBusy = true
    noiseEnabled = !noiseEnabled
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "noise-toggle"] })
  }

  function toggleKittyGlass() {
    kittyGlassMode = (kittyGlassMode + 1) % 3
    var opacity = kittyGlassMode === 0 ? "0.0" : (kittyGlassMode === 1 ? "0.5" : "1.0")
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "glass-set", opacity] })
  }

  function syncCornerRadius() {
    var rr = Settings.data.general.radiusRatio
    deferredProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "corner-sync", String(rr)] })
  }

  function toggleNiriBlurGlobal() {
    if (_niriBusy) return
    niriBlurGlobalEnabled = !niriBlurGlobalEnabled
    _niriBusy = true
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "blur-global-toggle"] })
  }

  function toggleNiriBlurPerWindow() {
    if (_niriBusy) return
    niriBlurWindowEnabled = !niriBlurWindowEnabled
    _niriBusy = true
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "blur-window-toggle"] })
  }

  property bool shadowEnabled: true

  function toggleNiriShadow() {
    if (_niriBusy) return
    _niriBusy = true
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "shadow-toggle"] })
  }

  function syncShadowColor() {
    if (_niriBusy) return
    _niriBusy = true
    niriProc.exec({ command: ["python3", _scriptsDir + "niri-toggle.py", "shadow-sync"] })
  }

  Rectangle {
    id: panelContainer
    anchors.fill: parent
    color: "transparent"

    Column {
      id: mainCol
      anchors { left: parent.left; right: parent.right; top: parent.top }
      anchors.margins: Style.marginM
      spacing: Style.marginS

      Item {
        width: parent.width; height: Style.fontSizeL * 1.6
        NIcon { icon: "settings-2"; color: Color.mPrimary; anchors.verticalCenter: parent.verticalCenter; x: 0 }
        NText {
          text: "Niri Config"
          pointSize: Style.fontSizeL
          font.weight: Font.Bold
          color: Color.mOnSurface
          anchors.verticalCenter: parent.verticalCenter
          x: Style.fontSizeL * 1.2
        }
      }

      Rectangle {
        width: parent.width
        height: compCol.implicitHeight + Style.marginS * 2
        color: Color.smartAlpha(Color.mSurfaceVariant); radius: Style.radiusL

        Column {
          id: compCol
          anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: Style.marginS }
          spacing: Style.marginS
          readonly property int btnSize: Math.floor(((width - Style.marginS * 4) / 5) * 0.88)

          NText { text: "Niri"; pointSize: Style.fontSizeXXS; color: Color.mOnSurfaceVariant; font.weight: Font.Bold }

          Row {
            spacing: Style.marginS
            anchors.horizontalCenter: parent.horizontalCenter
            Repeater {
              model: 5
              delegate: ToolBtn {
                readonly property var labels: ["Blur Global", "Blur Window", "Square Corners", "Focus Ring", "Niri Shadow"]
                readonly property int myIdx: index
                num: index + 1
                tooltip: myIdx === 0
                  ? "Blur Global: " + (root.niriBlurGlobalEnabled ? "On" : "Off")
                  : myIdx === 1
                    ? "Blur Window: " + (root.niriBlurWindowEnabled ? "On" : "Off")
                    : myIdx === 2
                      ? "Square Corners: " + (root.squareCorners ? "On" : "Off")
                      : myIdx === 3
                        ? "Focus Ring: " + (root.focusRingEnabled ? "On" : "Off")
                        : labels[index]
                width: compCol.btnSize; height: compCol.btnSize
                interactive: true
                onTriggered: {
                  if (myIdx === 0) root.toggleNiriBlurGlobal()
                  else if (myIdx === 1) root.toggleNiriBlurPerWindow()
                  else if (myIdx === 2) root.toggleSquareCorners()
                  else if (myIdx === 3) root.toggleFocusRing()
                  else if (myIdx === 4) root.toggleNiriShadow()
                }
              }
            }
          }

          Row {
            spacing: Style.marginS
            anchors.horizontalCenter: parent.horizontalCenter
            Repeater {
              model: 4
              delegate: ToolBtn {
                readonly property var labels: ["Sync Shadow", "Rainbow Ring", "Ring Width", "Noise & Sat"]
                readonly property int myIdx: index
                num: index + 6
                tooltip: myIdx === 1
                  ? (root.focusRingGradient ? "Rainbow: On" : "Rainbow: Off")
                  : myIdx === 2
                    ? "Width: " + root.focusRingWidth + "px"
                    : myIdx === 3
                      ? "Noise & Sat: " + (root.noiseEnabled ? "On" : "Off")
                      : labels[index]
                width: compCol.btnSize; height: compCol.btnSize
                interactive: true
                onTriggered: {
                  if (myIdx === 0) root.syncShadowColor()
                  else if (myIdx === 1) root.toggleFocusRingGradient()
                  else if (myIdx === 2) root.toggleFocusRingWidth()
                  else if (myIdx === 3) root.toggleNoiseSat()
                }
              }
            }
          }
        }
      }
    }
  }

  component ToolBtn: Item {
    id: btn
    property int    num:         0
    property bool   interactive: false
    property string tooltip:     ""
    signal triggered()

    Rectangle {
      anchors.centerIn: parent
      width:  Math.min(btn.width - 8, 42)
      height: Math.min(btn.height - 8, 42)
      radius: 8
      color: btn.interactive
        ? (btnMouse.containsMouse ? Color.mPrimary : Color.smartAlpha(Color.mSurface))
        : Color.smartAlpha(Color.mSurface)
      Behavior on color { ColorAnimation { duration: Style.animationFast } }

      NText {
        anchors.centerIn: parent
        text: num
        color: btnMouse.containsMouse && btn.interactive ? Color.mOnPrimary : Color.mOnSurfaceVariant
        pointSize: Style.fontSizeXXS
        font.weight: Font.Bold
      }

      NText {
        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: -14 }
        text: btn.tooltip
        color: Color.mOnSurface
        pointSize: Style.fontSizeXXS
        visible: btnMouse.containsMouse && btn.tooltip !== ""
        width: 120
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        z: 999
      }

      MouseArea {
        id: btnMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: btn.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (btn.interactive) btn.triggered()
      }
    }
  }
}
