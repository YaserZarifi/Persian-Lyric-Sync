import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root

    required property QtObject backend
    readonly property alias count: list.count

    ListView {
        id: list
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        model: root.backend.lines
        currentIndex: -1
        ScrollBar.vertical: ScrollBar {}

        delegate: LineDelegate {
            width: ListView.view.width
            onActivated: row => {
                list.currentIndex = row
                root.backend.requestPreview(root.backend.lines.midpoint(row))
            }
        }

        Label {
            anchors.centerIn: parent
            visible: list.count === 0
            text: qsTr("Import a lyrics .txt to get started")
            opacity: 0.6
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Label {
            Layout.fillWidth: true
            text: qsTr("Times are m:ss.cc or seconds. Enter to apply.")
            opacity: 0.6
            font.pixelSize: 12
        }
        Button {
            text: qsTr("Spread evenly")
            flat: true
            enabled: list.count > 0
            onClicked: root.backend.spreadEvenly()
        }
        Button {
            text: qsTr("Auto-time")
            highlighted: true
            enabled: root.backend.canAutoTime
            onClicked: root.backend.autoTime()
        }
    }
}
