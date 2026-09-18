import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

RowLayout {
    id: root

    required property string label
    required property string path
    property string placeholder: qsTr("Not selected")
    property alias nameFilters: dialog.nameFilters

    signal picked(url url)

    Label {
        Layout.preferredWidth: 90
        text: root.label
    }
    TextField {
        Layout.fillWidth: true
        readOnly: true
        text: root.path.split(/[\\/]/).pop()
        placeholderText: root.path ? "" : root.placeholder
        ToolTip.visible: hovered && root.path !== ""
        ToolTip.text: root.path
    }
    Button {
        text: qsTr("Browse…")
        onClicked: dialog.open()
    }

    FileDialog {
        id: dialog
        title: root.label
        onAccepted: root.picked(selectedFile)
    }
}
