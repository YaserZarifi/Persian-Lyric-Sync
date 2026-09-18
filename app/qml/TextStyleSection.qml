import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

GroupBox {
    id: root

    required property QtObject backend
    readonly property var style: backend.style
    readonly property var fonts: backend.fontList

    title: qsTr("Text")

    GridLayout {
        anchors.fill: parent
        columns: 4
        columnSpacing: 12

        Label { text: qsTr("Font") }
        RowLayout {
            Layout.columnSpan: 3
            Layout.fillWidth: true
            ComboBox {
                Layout.fillWidth: true
                model: root.fonts
                textRole: "family"
                currentIndex: Math.max(0, root.fonts.findIndex(f => f.file === root.style.font_file))
                onActivated: index => root.backend.setStyleValue("font_file", root.fonts[index].file)
            }
            Button {
                text: qsTr("Add…")
                flat: true
                onClicked: fontDialog.openRemembered()
            }
        }

        Label { text: qsTr("Size") }
        SpinBox {
            Layout.preferredWidth: 130
            from: 24; to: 220; stepSize: 4
            value: root.style.font_size
            editable: true
            onValueModified: root.backend.setStyleValue("font_size", value)
        }
        Label { text: qsTr("Position") }
        ComboBox {
            Layout.preferredWidth: 130
            readonly property var alignments: [5, 2, 8]
            model: [qsTr("Middle"), qsTr("Bottom"), qsTr("Top")]
            currentIndex: Math.max(0, alignments.indexOf(root.style.alignment))
            onActivated: index => root.backend.setStyleValue("alignment", alignments[index])
        }

        Label { text: qsTr("Outline") }
        SpinBox {
            Layout.preferredWidth: 130
            from: 0; to: 24
            value: root.style.outline_width
            editable: true
            onValueModified: root.backend.setStyleValue("outline_width", value)
        }
        Label { text: qsTr("Shadow") }
        SpinBox {
            Layout.preferredWidth: 130
            from: 0; to: 16
            value: root.style.shadow_depth
            editable: true
            onValueModified: root.backend.setStyleValue("shadow_depth", value)
        }

        Label { text: qsTr("Text color") }
        ColorPicker {
            color: root.style.fill_color
            onPicked: c => root.backend.setStyleValue("fill_color", c)
        }
        Label { text: qsTr("Outline color") }
        ColorPicker {
            color: root.style.outline_color
            onPicked: c => root.backend.setStyleValue("outline_color", c)
        }

        Label { text: qsTr("Entrance") }
        ComboBox {
            Layout.preferredWidth: 130
            readonly property var values: ["fade", "pop", "slide_up"]
            model: [qsTr("Fade"), qsTr("Pop"), qsTr("Slide up")]
            currentIndex: Math.max(0, values.indexOf(root.style.animation))
            onActivated: index => root.backend.setStyleValue("animation", values[index])
        }
        Label { text: qsTr("Fade in (ms)") }
        SpinBox {
            Layout.preferredWidth: 130
            from: 0; to: 2000; stepSize: 50
            value: root.style.fade_in_ms
            editable: true
            onValueModified: root.backend.setStyleValue("fade_in_ms", value)
        }

        Item { Layout.columnSpan: 2 }
        Label { text: qsTr("Fade out (ms)") }
        SpinBox {
            Layout.preferredWidth: 130
            from: 0; to: 2000; stepSize: 50
            value: root.style.fade_out_ms
            editable: true
            onValueModified: root.backend.setStyleValue("fade_out_ms", value)
        }
    }

    RememberingFileDialog {
        id: fontDialog
        memoryKey: "font"
        title: qsTr("Add a font")
        nameFilters: [qsTr("Fonts (*.ttf *.otf)")]
        onAccepted: root.backend.addFont(selectedFile)
    }
}
