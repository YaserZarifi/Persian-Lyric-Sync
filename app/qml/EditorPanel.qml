import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: root

    required property QtObject backend

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        FilePickerRow {
            Layout.fillWidth: true
            label: qsTr("Audio")
            path: root.backend.audioPath
            nameFilters: [qsTr("Audio (*.mp3 *.m4a *.wav *.flac *.ogg)")]
            onPicked: url => root.backend.setAudio(url)
        }
        FilePickerRow {
            Layout.fillWidth: true
            label: qsTr("Background")
            path: root.backend.backgroundPath
            nameFilters: [qsTr("Images (*.jpg *.jpeg *.png *.webp *.bmp)")]
            onPicked: url => root.backend.setBackground(url)
        }
        FilePickerRow {
            Layout.fillWidth: true
            label: qsTr("Lyrics")
            path: ""
            placeholder: qsTr("Import a .txt file (one line per lyric)")
            nameFilters: [qsTr("Text (*.txt)")]
            onPicked: url => root.backend.importLyrics(url)
        }

        TabBar {
            id: tabs
            objectName: "editorTabs"
            Layout.fillWidth: true
            TabButton { text: qsTr("Timing (%1 lines)").arg(linesList.count) }
            TabButton { text: qsTr("Lyrics text") }
            TabButton { text: qsTr("Style") }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            LinesList {
                id: linesList
                backend: root.backend
            }
            LyricsEditor {
                backend: root.backend
            }
            StylePanel {
                backend: root.backend
            }
        }
    }
}
