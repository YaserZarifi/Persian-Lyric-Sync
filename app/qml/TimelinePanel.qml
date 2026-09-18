import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "time.js" as Time

Pane {
    id: root

    required property QtObject backend
    required property AudioPlayer player

    padding: 8

    ColumnLayout {
        anchors.fill: parent
        spacing: 4

        RowLayout {
            Layout.fillWidth: true

            Button {
                text: root.player.playing ? qsTr("Pause") : qsTr("Play")
                enabled: root.backend.audioPath !== ""
                onClicked: root.player.toggle()
            }
            Label {
                text: qsTr("%1 / %2").arg(Time.format(root.backend.previewTime)).arg(Time.format(root.backend.duration))
                font.family: "Consolas"
            }
            Label {
                Layout.fillWidth: true
                text: qsTr("Drag a line to move it · drag its edges to resize · Shift+drag also moves every later line · Space play/pause · Ctrl+wheel zoom")
                opacity: 0.55
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            BusyIndicator {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                running: root.backend.autoTiming
                visible: running
            }
            ToolButton {
                text: qsTr("Auto-time")
                enabled: root.backend.canAutoTime
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Synced lyrics from LRCLIB if the song is there, otherwise a rough guess from the audio")
                onClicked: root.backend.autoTime()
            }
            ToolButton {
                text: qsTr("Guess rest from here")
                enabled: root.backend.canAutoTime
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Keep lines before the playhead, re-guess the rest from the audio")
                onClicked: root.backend.guessRestFromPlayhead()
            }
            ToolButton {
                text: qsTr("Undo")
                enabled: root.backend.lines.canUndo
                onClicked: root.backend.lines.undo()
            }
            ToolButton {
                text: qsTr("Fit")
                onClicked: timeline.fit()
            }
            ToolButton {
                text: "−"
                onClicked: timeline.zoomAt(1 / 1.5, timeline.width / 2)
            }
            ToolButton {
                text: "+"
                onClicked: timeline.zoomAt(1.5, timeline.width / 2)
            }
        }

        TimelineView {
            id: timeline
            objectName: "timeline"
            Layout.fillWidth: true
            Layout.fillHeight: true
            backend: root.backend
            player: root.player
        }
    }
}
