import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

ApplicationWindow {
    id: window

    required property QtObject backend

    width: 1560
    height: 1000
    visible: true
    title: qsTr("%1%2 — Persian Lyric Video")
        .arg(backend.projectPath ? backend.projectPath.split(/[\\/]/).pop() : qsTr("Untitled"))
        .arg(backend.dirty ? " *" : "")

    Material.theme: Material.Dark
    Material.accent: Material.Pink
    Material.primary: "#26262c"
    Material.foreground: "#eee"

    onClosing: close => {
        if (backend.dirty && !actions.forceQuit) {
            close.accepted = false
            actions.guard(() => {
                actions.forceQuit = true
                window.close()
            })
        }
    }

    ProjectActions {
        id: actions
        backend: window.backend
    }

    header: AppToolBar {
        backend: window.backend
        actions: actions
    }

    AudioPlayer {
        id: player
        backend: window.backend
    }

    Shortcut {
        sequence: "Space"
        onActivated: player.toggle()
    }

    Shortcut {
        sequence: "Left"
        onActivated: window.backend.nudgeSelected(-0.1)
    }
    Shortcut {
        sequence: "Right"
        onActivated: window.backend.nudgeSelected(0.1)
    }
    Shortcut {
        sequence: "Alt+Left"
        onActivated: window.backend.nudgeSelected(-0.02)
    }
    Shortcut {
        sequence: "Alt+Right"
        onActivated: window.backend.nudgeSelected(0.02)
    }
    Shortcut {
        sequence: "Shift+Left"
        onActivated: window.backend.rippleSelected(-0.1)
    }
    Shortcut {
        sequence: "Shift+Right"
        onActivated: window.backend.rippleSelected(0.1)
    }

    Shortcut {
        sequences: [StandardKey.Undo]
        onActivated: window.backend.lines.undo()
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Vertical

        SplitView {
            SplitView.fillHeight: true

            EditorPanel {
                SplitView.preferredWidth: 600
                SplitView.minimumWidth: 420
                backend: window.backend
            }

            PreviewPanel {
                SplitView.fillWidth: true
                backend: window.backend
            }
        }

        TimelinePanel {
            SplitView.preferredHeight: 250
            SplitView.minimumHeight: 180
            backend: window.backend
            player: player
        }
    }

    footer: StatusBar {
        backend: window.backend
    }
}
