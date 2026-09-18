import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    required property var model
    required property int index
    required property real pxPerSec
    required property QtObject lines
    required property real boundaryTop
    required property bool current

    readonly property bool dragging: moveDrag.active || rippleDrag.active
                                     || startDrag.active || endDrag.active
    readonly property real edgeWidth: Math.min(10, width / 3)

    signal seek(real t)

    x: model.start * pxPerSec
    width: Math.max(2, (model.end - model.start) * pxPerSec)
    radius: 4
    color: current ? "#b8336a" : (dragging ? "#4d6490" : "#34405a")
    border.color: dragging ? "#fff" : "#5a6b8f"

    // Boundary guides up through the waveform.
    Rectangle {
        y: root.boundaryTop
        width: 1
        height: -root.boundaryTop
        color: "#7fa3ff"
        opacity: 0.45
    }
    Rectangle {
        x: root.width - 1
        y: root.boundaryTop
        width: 1
        height: -root.boundaryTop
        color: "#ff9f7f"
        opacity: 0.45
    }

    Label {
        anchors.fill: parent
        anchors.leftMargin: root.edgeWidth + 2
        anchors.rightMargin: root.edgeWidth + 2
        visible: root.width > 30
        text: root.model.text
        font.family: "Vazirmatn FD"
        font.pixelSize: 14
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    TapHandler {
        gesturePolicy: TapHandler.ReleaseWithinBounds
        onTapped: root.seek(root.model.start)
    }

    TimelineDrag {
        id: moveDrag
        lines: root.lines
        row: root.index
        mode: "move"
        pxPerSec: root.pxPerSec
        acceptedModifiers: Qt.NoModifier
        cursorShape: Qt.SizeAllCursor
    }

    TimelineDrag {
        id: rippleDrag
        lines: root.lines
        row: root.index
        mode: "ripple"
        pxPerSec: root.pxPerSec
        acceptedModifiers: Qt.ShiftModifier
        cursorShape: Qt.SizeAllCursor
    }

    Item {
        width: root.edgeWidth
        height: root.height

        HoverHandler {
            cursorShape: Qt.SizeHorCursor
        }
        TimelineDrag {
            id: startDrag
            lines: root.lines
            row: root.index
            mode: "start"
            pxPerSec: root.pxPerSec
            // Edges win over the body's move/ripple handlers that share the press.
            grabPermissions: PointerHandler.CanTakeOverFromAnything
        }
    }

    Item {
        x: root.width - width
        width: root.edgeWidth
        height: root.height

        HoverHandler {
            cursorShape: Qt.SizeHorCursor
        }
        TimelineDrag {
            id: endDrag
            lines: root.lines
            row: root.index
            mode: "end"
            pxPerSec: root.pxPerSec
            // Edges win over the body's move/ripple handlers that share the press.
            grabPermissions: PointerHandler.CanTakeOverFromAnything
        }
    }
}
