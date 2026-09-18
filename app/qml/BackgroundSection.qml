import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

GroupBox {
    id: root

    required property QtObject backend
    readonly property var style: backend.style

    title: qsTr("Background")

    GridLayout {
        anchors.fill: parent
        columns: 2
        columnSpacing: 12

        Label { text: qsTr("Motion") }
        ComboBox {
            readonly property var values: ["off", "zoom_in", "zoom_out", "pan_left", "pan_right"]
            Layout.fillWidth: true
            model: [qsTr("Still"), qsTr("Slow zoom in"), qsTr("Slow zoom out"), qsTr("Pan left → right"), qsTr("Pan right → left")]
            currentIndex: Math.max(0, values.indexOf(root.style.ken_burns))
            onActivated: index => root.backend.setStyleValue("ken_burns", values[index])
        }

        Label { text: qsTr("Motion amount") }
        LabeledSlider {
            Layout.fillWidth: true
            enabled: root.style.ken_burns !== "off"
            from: 0.02; to: 0.35; stepSize: 0.01
            value: root.style.ken_burns_amount
            displayScale: 100; suffix: "%"
            onCommitted: v => root.backend.setStyleValue("ken_burns_amount", Math.round(v * 100) / 100)
        }

        Label { text: qsTr("Darken") }
        LabeledSlider {
            Layout.fillWidth: true
            from: 0; to: 0.8; stepSize: 0.05
            value: root.style.bg_dim
            displayScale: 100; suffix: "%"
            onCommitted: v => root.backend.setStyleValue("bg_dim", Math.round(v * 100) / 100)
        }

        Label { text: qsTr("Blur") }
        LabeledSlider {
            Layout.fillWidth: true
            from: 0; to: 20; stepSize: 1
            value: root.style.bg_blur
            onCommitted: v => root.backend.setStyleValue("bg_blur", Math.round(v))
        }
    }
}
