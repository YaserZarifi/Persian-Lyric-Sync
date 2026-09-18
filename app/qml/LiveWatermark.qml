import QtQuick

Item {
    id: root

    required property QtObject backend
    readonly property var style: backend.style
    readonly property real k: height / 1080
    readonly property bool atLeft: style.watermark_position.endsWith("left")
    readonly property bool atTop: style.watermark_position.startsWith("top")
    readonly property real margin: 40 * k

    Column {
        x: root.atLeft ? root.margin : root.width - width - root.margin
        y: root.atTop ? root.margin : root.height - height - root.margin
        spacing: 10 * root.k
        opacity: root.style.watermark_opacity

        Image {
            anchors.right: root.atLeft ? undefined : parent.right
            visible: root.style.watermark_url !== ""
            source: root.style.watermark_url
            width: root.width * root.style.watermark_scale
            height: implicitHeight > 0 ? width * implicitHeight / implicitWidth : 0
            fillMode: Image.PreserveAspectFit
        }
        Text {
            anchors.right: root.atLeft ? undefined : parent.right
            visible: text !== ""
            text: root.style.watermark_text
            color: root.style.fill_color
            style: Text.Outline
            styleColor: root.style.outline_color
            font.family: root.style.qt_family
            font.pixelSize: 34 * root.style.em_ratio * root.k
            font.weight: root.style.qt_weight
        }
    }
}
