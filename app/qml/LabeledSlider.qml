import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root

    required property real value
    property real from: 0
    property real to: 1
    property real stepSize: 0.01
    property string suffix: ""
    property real displayScale: 1
    property int decimals: 0

    signal committed(real value)

    Slider {
        id: slider
        Layout.fillWidth: true
        from: root.from
        to: root.to
        stepSize: root.stepSize
        value: root.value
        live: true
        onPressedChanged: {
            if (!pressed)
                root.committed(value)
        }
    }
    Label {
        Layout.preferredWidth: 52
        horizontalAlignment: Text.AlignRight
        text: (slider.value * root.displayScale).toFixed(root.decimals) + root.suffix
    }
}
