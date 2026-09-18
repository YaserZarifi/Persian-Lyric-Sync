import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root

    required property QtObject backend

    Label { text: qsTr("Preset") }
    ComboBox {
        Layout.fillWidth: true
        model: root.backend.presetNames
        currentIndex: Math.max(0, root.backend.presetNames.indexOf(root.backend.currentPreset))
        displayText: root.backend.styleModified ? qsTr("%1 (modified)").arg(currentText) : currentText
        onActivated: index => root.backend.loadPreset(root.backend.presetNames[index])
    }
    Button {
        text: qsTr("Save as…")
        onClicked: saveDialog.open()
    }
    Button {
        text: qsTr("Delete")
        flat: true
        enabled: root.backend.presetIsUser
        onClicked: root.backend.deletePreset()
    }

    Dialog {
        id: saveDialog
        title: qsTr("Save style preset")
        modal: true
        anchors.centerIn: Overlay.overlay
        standardButtons: Dialog.Save | Dialog.Cancel
        onOpened: {
            nameField.text = root.backend.currentPreset === "default-bold-outline" ? "" : root.backend.currentPreset
            nameField.forceActiveFocus()
        }
        onAccepted: root.backend.savePresetAs(nameField.text)

        TextField {
            id: nameField
            width: 320
            placeholderText: qsTr("Preset name, e.g. my-channel")
            onAccepted: saveDialog.accept()
        }
    }
}
