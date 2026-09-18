import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ToolBar {
    id: root

    required property QtObject backend

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12

        Label {
            Layout.fillWidth: true
            text: root.backend.status
            elide: Text.ElideRight
        }
        ProgressBar {
            Layout.preferredWidth: 280
            visible: root.backend.exporting || root.backend.exportProgress > 0
            value: root.backend.exportProgress
        }
        Label {
            visible: root.backend.exporting
            text: qsTr("%1%").arg(Math.round(root.backend.exportProgress * 100))
        }
    }
}
