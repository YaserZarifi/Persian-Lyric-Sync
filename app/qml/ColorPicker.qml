import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

RowLayout {
    id: root

    required property color color

    signal picked(string color)

    Rectangle {
        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        radius: 4
        color: root.color
        border.color: "#888"
    }
    Button {
        text: qsTr("Change…")
        flat: true
        onClicked: dialog.open()
    }

    ColorDialog {
        id: dialog
        selectedColor: root.color
        onAccepted: root.picked(selectedColor.toString())
    }
}
