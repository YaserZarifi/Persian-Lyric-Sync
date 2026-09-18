import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root

    required property string label
    required property string path
    required property string memoryKey
    property string placeholder: qsTr("Not selected")
    property alias nameFilters: dialog.nameFilters
    property string extraText: ""
    property bool extraEnabled: true

    signal picked(url url)
    signal extraClicked()

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
        onClicked: dialog.openRemembered()
    }
    Button {
        visible: root.extraText !== ""
        enabled: root.extraEnabled
        text: root.extraText
        flat: true
        onClicked: root.extraClicked()
    }

    RememberingFileDialog {
        id: dialog
        title: root.label
        memoryKey: root.memoryKey
        onAccepted: root.picked(selectedFile)
    }
}
