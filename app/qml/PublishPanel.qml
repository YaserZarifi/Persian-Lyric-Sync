import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root

    required property QtObject backend
    readonly property var info: backend.publish

    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 12

        GroupBox {
            Layout.fillWidth: true
            title: qsTr("Song")

            GridLayout {
                anchors.fill: parent
                columns: 2
                columnSpacing: 12

                Label { text: qsTr("Artist (فارسی)") }
                TextField {
                    Layout.fillWidth: true
                    text: root.info.artist_fa
                    horizontalAlignment: TextInput.AlignRight
                    font.family: "Vazirmatn FD"
                    onEditingFinished: root.backend.setPublishValue("artist_fa", text)
                }
                Label { text: qsTr("Artist (English)") }
                TextField {
                    Layout.fillWidth: true
                    text: root.info.artist_en
                    onEditingFinished: root.backend.setPublishValue("artist_en", text)
                }
                Label { text: qsTr("Song (فارسی)") }
                TextField {
                    Layout.fillWidth: true
                    text: root.info.title_fa
                    horizontalAlignment: TextInput.AlignRight
                    font.family: "Vazirmatn FD"
                    onEditingFinished: root.backend.setPublishValue("title_fa", text)
                }
                Label { text: qsTr("Song (English)") }
                TextField {
                    Layout.fillWidth: true
                    text: root.info.title_en
                    onEditingFinished: root.backend.setPublishValue("title_en", text)
                }
                Label { text: qsTr("Label") }
                TextField {
                    Layout.fillWidth: true
                    text: root.info.label
                    placeholderText: qsTr("Optional")
                    onEditingFinished: root.backend.setPublishValue("label", text)
                }
            }
        }

        GroupBox {
            Layout.fillWidth: true
            title: qsTr("Rights")

            GridLayout {
                anchors.fill: parent
                columns: 2
                columnSpacing: 12

                Label { text: qsTr("Status") }
                ComboBox {
                    readonly property var values: ["needs_review", "permission", "content_id", "royalty_free"]
                    Layout.fillWidth: true
                    model: [qsTr("Needs review before publishing"), qsTr("Permission obtained"),
                            qsTr("Accepting a Content ID claim"), qsTr("Royalty-free")]
                    currentIndex: Math.max(0, values.indexOf(root.info.rights_status))
                    onActivated: index => root.backend.setPublishValue("rights_status", values[index])
                }
                Label { text: qsTr("Notes") }
                TextField {
                    Layout.fillWidth: true
                    text: root.info.rights_notes
                    placeholderText: qsTr("Added to the description, e.g. who gave permission")
                    onEditingFinished: root.backend.setPublishValue("rights_notes", text)
                }
                Label {
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    visible: root.info.rights_status === "needs_review"
                    text: qsTr("⚠ Rights not checked yet: the description gets no rights statement until you choose a status.")
                    color: "#ffb74d"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Button {
                text: qsTr("Write with AI")
                highlighted: true
                enabled: !root.backend.publishBusy
                onClicked: root.backend.generatePublish()
            }
            BusyIndicator {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                running: root.backend.publishBusy
                visible: running
            }
            Button {
                text: qsTr("Fill from template")
                flat: true
                onClicked: root.backend.fillPublishTemplate()
            }
            Item { Layout.fillWidth: true }
            Button {
                text: qsTr("AI settings…")
                flat: true
                onClicked: aiDialog.open()
            }
        }

        GroupBox {
            Layout.fillWidth: true
            title: root.info.generated_by ? qsTr("YouTube (written by %1)").arg(root.info.generated_by)
                                          : qsTr("YouTube")

            ColumnLayout {
                anchors.fill: parent

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Title (%1/100)").arg(titleField.text.length)
                        color: titleField.text.length > 100 ? "#ff6e6e" : palette.text
                    }
                    Button {
                        text: qsTr("Copy")
                        flat: true
                        onClicked: root.backend.copyText(titleField.text)
                    }
                }
                TextField {
                    id: titleField
                    Layout.fillWidth: true
                    text: root.info.youtube_title
                    font.family: "Vazirmatn FD"
                    onEditingFinished: root.backend.setPublishValue("youtube_title", text)
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Description")
                    }
                    Button {
                        text: qsTr("Copy")
                        flat: true
                        onClicked: root.backend.copyText(descField.text)
                    }
                }
                TextArea {
                    id: descField
                    Layout.fillWidth: true
                    Layout.preferredHeight: 220
                    text: root.info.description
                    wrapMode: TextEdit.Wrap
                    font.family: "Vazirmatn FD"
                    font.pixelSize: 14
                    onEditingFinished: root.backend.setPublishValue("description", text)
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Tags")
                    }
                    Button {
                        text: qsTr("Copy")
                        flat: true
                        onClicked: root.backend.copyText(tagsField.text)
                    }
                }
                TextField {
                    id: tagsField
                    Layout.fillWidth: true
                    text: root.info.hashtags_text
                    font.family: "Vazirmatn FD"
                    onEditingFinished: root.backend.setPublishValue("hashtags", text)
                }
            }
        }
    }

    AiSettingsDialog {
        id: aiDialog
        backend: root.backend
    }
}
