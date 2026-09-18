import QtCore
import QtQuick
import QtQuick.Dialogs

// FileDialog that reopens in the folder last used for the same purpose.
FileDialog {
    id: root

    required property string memoryKey
    readonly property Settings memory: Settings {
        category: "folders"
    }

    function openRemembered() {
        const folder = memory.value(memoryKey, "")
        if (folder)
            currentFolder = folder
        open()
    }

    onAccepted: {
        const file = String(selectedFile)
        memory.setValue(memoryKey, file.substring(0, file.lastIndexOf("/")))
    }
}
