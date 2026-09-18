import QtQuick
import QtQuick.Effects

// Qt stand-in for the exported background during playback: same crop, Ken Burns
// motion, darkening and blur as the ffmpeg graph.
Item {
    id: root

    required property QtObject backend
    readonly property var style: backend.style
    readonly property real progress: backend.duration > 0
                                     ? Math.max(0, Math.min(1, backend.previewTime / backend.duration)) : 0
    readonly property real amount: style.ken_burns_amount
    readonly property real zoom: {
        switch (style.ken_burns) {
        case "zoom_in": return 1 + amount * progress
        case "zoom_out": return 1 + amount * (1 - progress)
        case "pan_left":
        case "pan_right": return 1 + amount
        default: return 1
        }
    }
    // Horizontal position of the visible window: 0 = left edge, 1 = right edge.
    readonly property real panX: style.ken_burns === "pan_left" ? progress
                               : style.ken_burns === "pan_right" ? 1 - progress : 0.5

    clip: true

    Image {
        id: photo
        width: root.width * root.zoom
        height: root.height * root.zoom
        x: -(width - root.width) * root.panX
        y: -(height - root.height) / 2
        fillMode: Image.PreserveAspectCrop
        source: root.backend.backgroundUrl
        sourceSize.width: 1920
        asynchronous: true
        visible: root.style.bg_blur <= 0
    }

    MultiEffect {
        anchors.fill: photo
        source: photo
        visible: root.style.bg_blur > 0
        blurEnabled: true
        blurMax: 64
        blur: Math.min(1, root.style.bg_blur / 20)
    }

    Rectangle {
        anchors.fill: parent
        color: "black"
        opacity: root.style.bg_dim
    }
}
