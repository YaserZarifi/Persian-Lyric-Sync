import QtQuick

// Qt-rendered stand-in for the libass lyric, used while audio is playing.
Item {
    id: root

    required property QtObject backend
    readonly property var style: backend.style
    readonly property var line: backend.currentLine
    readonly property real k: height / 1080
    readonly property real outline: style.outline_width * k
    readonly property real t: backend.previewTime
    readonly property var anchorsByAlignment: ({ 2: "bottom", 5: "center", 8: "top" })
    readonly property string vAnchor: anchorsByAlignment[style.alignment] || "center"

    opacity: {
        if (!line.text)
            return 0
        const fin = style.fade_in_ms / 1000, fout = style.fade_out_ms / 1000
        let o = 1
        if (fin > 0)
            o = Math.min(o, (t - line.start) / fin)
        if (fout > 0)
            o = Math.min(o, (line.end - t) / fout)
        return Math.max(0, Math.min(1, o))
    }

    Item {
        id: block
        x: root.style.margin_h * root.k
        width: root.width - 2 * x
        height: mainText.contentHeight
        y: root.vAnchor === "top" ? root.style.margin_v * root.k
           : root.vAnchor === "bottom" ? root.height - height - root.style.margin_v * root.k
           : (root.height - height) / 2

        LyricText {
            x: root.style.shadow_depth * root.k
            y: root.style.shadow_depth * root.k
            width: block.width
            text: root.line.text
            pixelSize: mainText.pixelSize
            color: root.style.shadow_color
            opacity: 1 - root.style.shadow_alpha / 255
            visible: root.style.shadow_depth > 0
        }

        Repeater {
            model: root.outline > 0 ? 16 : 0

            LyricText {
                required property int index
                x: root.outline * Math.cos(index * Math.PI / 8)
                y: root.outline * Math.sin(index * Math.PI / 8)
                width: block.width
                text: root.line.text
                pixelSize: mainText.pixelSize
                color: root.style.outline_color
            }
        }

        LyricText {
            id: mainText
            width: block.width
            text: root.line.text
            pixelSize: root.style.font_size * root.style.em_ratio * root.k
            color: root.style.fill_color
        }
    }
}
