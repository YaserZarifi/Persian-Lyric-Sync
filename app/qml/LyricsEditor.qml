import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root

    required property QtObject backend

    ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true

        TextArea {
            id: editor
            text: root.backend.lyricsText
            font.family: "Vazirmatn FD"
            font.pixelSize: 18
            horizontalAlignment: TextEdit.AlignRight
            wrapMode: TextEdit.Wrap
            placeholderText: qsTr("Paste lyrics here, one line per lyric")
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Label {
            Layout.fillWidth: true
            text: qsTr("Same line count keeps timing; otherwise it is spread evenly.")
            opacity: 0.6
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
        Button {
            text: qsTr("Revert")
            onClicked: editor.text = Qt.binding(() => root.backend.lyricsText)
        }
        Button {
            text: qsTr("Apply")
            highlighted: true
            onClicked: {
                root.backend.applyLyricsText(editor.text)
                editor.text = Qt.binding(() => root.backend.lyricsText)
            }
        }
    }
}
