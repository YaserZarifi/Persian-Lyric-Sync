import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "time.js" as Time

Pane {
    id: root

    required property QtObject backend

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            id: stage
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#111"

            Item {
                id: frame
                objectName: "previewFrame"
                width: Math.min(stage.width, stage.height * 16 / 9)
                height: width * 9 / 16
                anchors.centerIn: parent
                clip: true

                Image {
                    anchors.fill: parent
                    visible: !root.backend.playing
                    fillMode: Image.PreserveAspectFit
                    source: root.backend.previewUrl
                    sourceSize.width: 1920
                    cache: false
                    asynchronous: true
                }

                Image {
                    anchors.fill: parent
                    visible: root.backend.playing
                    fillMode: Image.PreserveAspectCrop
                    source: root.backend.backgroundUrl
                    sourceSize.width: 1920
                    asynchronous: true
                }

                LiveLyric {
                    anchors.fill: parent
                    visible: root.backend.playing
                    backend: root.backend
                }

                Label {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.margins: 8
                    visible: root.backend.playing
                    text: qsTr("Live preview · pause for the exact render")
                    font.pixelSize: 11
                    padding: 4
                    background: Rectangle {
                        color: "#000"
                        opacity: 0.55
                        radius: 3
                    }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: !root.backend.canPreview
                text: qsTr("Pick a background image to see the preview")
                opacity: 0.6
            }
            BusyIndicator {
                anchors.right: parent.right
                anchors.top: parent.top
                running: root.backend.previewBusy
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Slider {
                id: timeSlider
                Layout.fillWidth: true
                from: 0
                to: Math.max(root.backend.duration, 1)
                value: root.backend.previewTime
                enabled: root.backend.canPreview
                onMoved: root.backend.requestPreview(value)
            }
            Label {
                text: qsTr("%1 / %2").arg(Time.format(timeSlider.value)).arg(Time.format(root.backend.duration))
            }
        }
    }
}
