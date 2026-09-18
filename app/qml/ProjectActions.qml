import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

Item {
    id: root

    required property QtObject backend
    property var pendingAction: null
    property bool forceQuit: false

    readonly property alias newAction: newAction
    readonly property alias openAction: openAction
    readonly property alias saveAction: saveAction
    readonly property alias saveAsAction: saveAsAction
    readonly property alias exportAction: exportAction

    function guard(action) {
        if (!backend.dirty) {
            action()
            return
        }
        pendingAction = action
        discardDialog.open()
    }

    function save() {
        if (!backend.saveProject())
            saveDialog.openRemembered()
    }

    Action {
        id: newAction
        text: qsTr("New")
        shortcut: StandardKey.New
        onTriggered: root.guard(() => root.backend.newProject())
    }

    Action {
        id: openAction
        text: qsTr("Open…")
        shortcut: StandardKey.Open
        onTriggered: root.guard(() => openDialog.openRemembered())
    }

    Action {
        id: saveAction
        text: qsTr("Save")
        shortcut: StandardKey.Save
        onTriggered: root.save()
    }

    Action {
        id: saveAsAction
        text: qsTr("Save As…")
        shortcut: StandardKey.SaveAs
        onTriggered: saveDialog.openRemembered()
    }

    Action {
        id: exportAction
        text: qsTr("Export MP4…")
        shortcut: "Ctrl+E"
        enabled: root.backend.canExport && !root.backend.exporting
        onTriggered: exportSettingsDialog.open()
    }

    ExportDialog {
        id: exportSettingsDialog
        backend: root.backend
        onChooseFile: exportDialog.openRemembered()
    }

    RememberingFileDialog {
        id: openDialog
        memoryKey: "project"
        title: qsTr("Open project")
        nameFilters: [qsTr("Lyric projects (*.json)")]
        onAccepted: root.backend.openProject(selectedFile)
    }

    RememberingFileDialog {
        id: saveDialog
        memoryKey: "project"
        title: qsTr("Save project")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "lyricproj.json"
        nameFilters: [qsTr("Lyric projects (*.lyricproj.json)")]
        onAccepted: root.backend.saveProjectAs(selectedFile)
    }

    RememberingFileDialog {
        id: exportDialog
        memoryKey: "export"
        title: qsTr("Export video")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "mp4"
        nameFilters: [qsTr("MP4 video (*.mp4)")]
        onAccepted: root.backend.exportVideo(selectedFile)
    }

    MessageDialog {
        id: discardDialog
        title: qsTr("Unsaved changes")
        text: qsTr("The current project has unsaved changes. Discard them?")
        buttons: MessageDialog.Discard | MessageDialog.Cancel
        onButtonClicked: (button, role) => {
            if (button === MessageDialog.Discard && root.pendingAction)
                root.pendingAction()
            root.pendingAction = null
        }
    }

    MessageDialog {
        id: errorDialog
        title: qsTr("Error")
        buttons: MessageDialog.Ok
    }

    Connections {
        target: root.backend
        function onErrorOccurred(message) {
            errorDialog.text = message
            errorDialog.open()
        }
    }
}
