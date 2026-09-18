import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ToolBar {
    id: root

    required property QtObject backend
    required property ProjectActions actions

    RowLayout {
        anchors.fill: parent

        ToolButton { action: root.actions.newAction }
        ToolButton { action: root.actions.openAction }
        ToolButton { action: root.actions.saveAction }
        ToolButton { action: root.actions.saveAsAction }

        Item { Layout.fillWidth: true }

        ToolButton {
            text: qsTr("Cancel export")
            visible: root.backend.exporting
            onClicked: root.backend.cancelExport()
        }
        ToolButton {
            action: root.actions.exportAction
            highlighted: true
        }
    }
}
