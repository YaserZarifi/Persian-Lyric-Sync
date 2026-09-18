import QtQuick
import QtQuick.Controls
import LyricVid
import "time.js" as Time

Rectangle {
    id: root

    required property QtObject backend
    required property AudioPlayer player

    property real pxPerSec: 40
    readonly property real duration: Math.max(backend.duration, 1)
    readonly property real minPxPerSec: Math.max(1, (width - 20) / duration)
    readonly property real maxPxPerSec: 600
    readonly property real cursorTime: backend.previewTime
    readonly property int rulerHeight: 22
    readonly property int laneHeight: 46
    readonly property real tickStep: {
        const steps = [0.5, 1, 2, 5, 10, 15, 30, 60, 120]
        for (const s of steps)
            if (s * pxPerSec >= 70)
                return s
        return 300
    }

    function zoomAt(factor, viewX) {
        const t = (flick.contentX + viewX) / pxPerSec
        pxPerSec = Math.max(minPxPerSec, Math.min(maxPxPerSec, pxPerSec * factor))
        flick.contentX = Math.max(0, Math.min(t * pxPerSec - viewX, flick.contentWidth - flick.width))
    }

    function fit() {
        pxPerSec = minPxPerSec
        flick.contentX = 0
    }

    color: "#17171b"
    radius: 4
    clip: true

    onCursorTimeChanged: {
        if (!player.playing)
            return
        const x = cursorTime * pxPerSec - flick.contentX
        if (x > flick.width * 0.85 || x < 0)
            flick.contentX = Math.max(0, Math.min(cursorTime * pxPerSec - flick.width * 0.2,
                                                  flick.contentWidth - flick.width))
    }

    WaveformItem {
        x: 0
        y: root.rulerHeight
        width: root.width
        height: root.height - root.rulerHeight - root.laneHeight - 14
        source: root.backend
        viewStart: flick.contentX / root.pxPerSec
        pxPerSec: root.pxPerSec
        color: "#4a5a7c"
    }

    Flickable {
        id: flick
        anchors.fill: parent
        contentWidth: Math.max(width, root.duration * root.pxPerSec)
        contentHeight: height
        flickableDirection: Flickable.HorizontalFlick
        boundsBehavior: Flickable.StopAtBounds
        interactive: false
        ScrollBar.horizontal: ScrollBar {
            policy: ScrollBar.AlwaysOn
        }

        Item {
            width: flick.contentWidth
            height: flick.height

            Item {
                anchors.fill: parent

                TapHandler {
                    onTapped: eventPoint => root.backend.requestPreview(
                        Math.max(0, Math.min(root.duration, eventPoint.position.x / root.pxPerSec)))
                }
            }

            Repeater {
                model: Math.floor(root.duration / root.tickStep) + 1

                Item {
                    required property int index
                    x: index * root.tickStep * root.pxPerSec
                    height: root.height

                    Rectangle {
                        width: 1
                        height: root.rulerHeight
                        color: "#555"
                    }
                    Label {
                        x: 4
                        y: 2
                        text: Time.format(parent.index * root.tickStep).replace(/\.00$/, "")
                        font.pixelSize: 11
                        opacity: 0.6
                    }
                }
            }

            Repeater {
                model: root.backend.lines

                delegate: LineBlock {
                    y: root.height - root.laneHeight - 14
                    height: root.laneHeight
                    pxPerSec: root.pxPerSec
                    lines: root.backend.lines
                    boundaryTop: -(y - root.rulerHeight)
                    current: root.cursorTime >= model.start && root.cursorTime < model.end
                    onSeek: t => root.backend.requestPreview(t)
                }
            }

            Rectangle {
                x: root.cursorTime * root.pxPerSec
                width: 2
                height: root.height
                color: "#ff4f8b"
            }
        }
    }

    WheelHandler {
        acceptedModifiers: Qt.ControlModifier
        onWheel: event => root.zoomAt(event.angleDelta.y > 0 ? 1.25 : 0.8, event.x)
    }

    WheelHandler {
        acceptedModifiers: Qt.NoModifier
        onWheel: event => {
            const delta = event.angleDelta.x !== 0 ? event.angleDelta.x : event.angleDelta.y
            flick.contentX = Math.max(0, Math.min(flick.contentX - delta,
                                                  flick.contentWidth - flick.width))
        }
    }

    Label {
        anchors.centerIn: parent
        visible: root.backend.audioPath === ""
        text: qsTr("Pick an audio file to see the timeline")
        opacity: 0.6
    }
}
