import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root

    required property QtObject backend

    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 12

        PresetBar {
            Layout.fillWidth: true
            backend: root.backend
        }
        TextStyleSection {
            Layout.fillWidth: true
            backend: root.backend
        }
        BackgroundSection {
            Layout.fillWidth: true
            backend: root.backend
        }
        WatermarkSection {
            Layout.fillWidth: true
            backend: root.backend
        }
    }
}
