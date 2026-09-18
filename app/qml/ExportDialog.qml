import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root

    required property QtObject backend
    readonly property var settings: backend.exportSettings

    signal chooseFile()

    title: qsTr("Export video")
    modal: true
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.Cancel

    GridLayout {
        columns: 2
        columnSpacing: 16

        Label { text: qsTr("Resolution") }
        ComboBox {
            readonly property var values: ["1920x1080", "2560x1440", "3840x2160"]
            Layout.preferredWidth: 260
            model: [qsTr("1080p (1920×1080)"), qsTr("1440p (2560×1440)"), qsTr("4K (3840×2160)")]
            currentIndex: Math.max(0, values.indexOf(root.settings.resolution))
            onActivated: index => root.backend.setExportValue("resolution", values[index])
        }

        Label { text: qsTr("Frame rate") }
        ComboBox {
            readonly property var values: [30, 60]
            Layout.preferredWidth: 260
            model: [qsTr("30 fps"), qsTr("60 fps (smoother motion, slower export)")]
            currentIndex: Math.max(0, values.indexOf(root.settings.fps))
            onActivated: index => root.backend.setExportValue("fps", values[index])
        }

        Label { text: qsTr("Encoder") }
        ComboBox {
            readonly property var values: ["auto", "gpu", "cpu"]
            Layout.preferredWidth: 260
            model: [qsTr("Automatic"), qsTr("GPU (NVIDIA NVENC)"), qsTr("CPU (x264)")]
            currentIndex: Math.max(0, values.indexOf(root.settings.encoder))
            onActivated: index => root.backend.setExportValue("encoder", values[index])
        }

        Label {
            Layout.columnSpan: 2
            text: root.settings.gpu ? qsTr("NVIDIA GPU encoder available.")
                                    : qsTr("No NVIDIA GPU encoder found; Automatic uses the CPU.")
            opacity: 0.6
            font.pixelSize: 12
        }

        Button {
            Layout.columnSpan: 2
            Layout.alignment: Qt.AlignRight
            text: qsTr("Choose file and export…")
            highlighted: true
            onClicked: {
                root.close()
                root.chooseFile()
            }
        }
    }
}
