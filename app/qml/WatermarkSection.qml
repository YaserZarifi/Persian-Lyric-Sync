import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

GroupBox {
    id: root

    required property QtObject backend
    readonly property var style: backend.style

    title: qsTr("Watermark")

    GridLayout {
        anchors.fill: parent
        columns: 2
        columnSpacing: 12

        Label { text: qsTr("Logo") }
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: root.style.watermark_image ? root.style.watermark_image.split(/[\\/]/).pop() : qsTr("None")
                elide: Text.ElideMiddle
                opacity: root.style.watermark_image ? 1 : 0.6
            }
            Button {
                text: qsTr("Choose…")
                flat: true
                onClicked: logoDialog.open()
            }
            Button {
                text: qsTr("Clear")
                flat: true
                visible: root.style.watermark_image !== ""
                onClicked: root.backend.setStyleValue("watermark_image", "")
            }
        }

        Label { text: qsTr("Text") }
        TextField {
            Layout.fillWidth: true
            text: root.style.watermark_text
            placeholderText: qsTr("e.g. @YourChannel")
            onEditingFinished: root.backend.setStyleValue("watermark_text", text)
        }

        Label { text: qsTr("Corner") }
        ComboBox {
            readonly property var values: ["top_left", "top_right", "bottom_left", "bottom_right"]
            Layout.fillWidth: true
            model: [qsTr("Top left"), qsTr("Top right"), qsTr("Bottom left"), qsTr("Bottom right")]
            currentIndex: Math.max(0, values.indexOf(root.style.watermark_position))
            onActivated: index => root.backend.setStyleValue("watermark_position", values[index])
        }

        Label { text: qsTr("Logo size") }
        LabeledSlider {
            Layout.fillWidth: true
            from: 0.04; to: 0.3; stepSize: 0.01
            value: root.style.watermark_scale
            displayScale: 100; suffix: "%"
            onCommitted: v => root.backend.setStyleValue("watermark_scale", Math.round(v * 100) / 100)
        }

        Label { text: qsTr("Opacity") }
        LabeledSlider {
            Layout.fillWidth: true
            from: 0.2; to: 1; stepSize: 0.05
            value: root.style.watermark_opacity
            displayScale: 100; suffix: "%"
            onCommitted: v => root.backend.setStyleValue("watermark_opacity", Math.round(v * 100) / 100)
        }
    }

    FileDialog {
        id: logoDialog
        title: qsTr("Choose a logo")
        nameFilters: [qsTr("Images (*.png *.webp *.jpg *.jpeg)")]
        onAccepted: root.backend.setWatermarkImage(selectedFile)
    }
}
