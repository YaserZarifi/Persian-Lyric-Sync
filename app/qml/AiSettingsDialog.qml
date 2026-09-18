import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root

    required property QtObject backend

    title: qsTr("AI settings")
    modal: true
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.Save | Dialog.Cancel

    onOpened: {
        urlField.text = backend.aiSettings.url
        tokenField.text = ""
        testResult.text = ""
    }
    onAccepted: backend.setAiSettings(urlField.text, tokenField.text)

    ColumnLayout {
        width: 460
        spacing: 8

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: qsTr("The app asks your own Cloudflare Worker (see worker/README.md in the project) to write the text. Workers AI is tried first (free); Claude and Gemini join automatically when their keys are set on the Worker.")
            opacity: 0.75
            font.pixelSize: 12
        }
        Label { text: qsTr("Worker URL") }
        TextField {
            id: urlField
            Layout.fillWidth: true
            placeholderText: "https://persian-lyric-sync-ai.<you>.workers.dev"
        }
        Label { text: qsTr("App token") }
        TextField {
            id: tokenField
            Layout.fillWidth: true
            echoMode: TextInput.Password
            placeholderText: root.backend.aiSettings.hasToken ? qsTr("Saved (leave empty to keep)")
                                                              : qsTr("The APP_TOKEN secret you set on the Worker")
        }
        RowLayout {
            Button {
                text: qsTr("Test connection")
                flat: true
                onClicked: {
                    root.backend.setAiSettings(urlField.text, tokenField.text)
                    testResult.text = root.backend.testAiConnection()
                }
            }
            Label {
                id: testResult
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font.pixelSize: 12
            }
        }
    }
}
