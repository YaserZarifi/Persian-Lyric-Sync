import QtQuick

// Horizontal drag that reports seconds moved to the lines model. activeTranslation is
// measured in scene space, so the block moving under the pointer doesn't feed back.
DragHandler {
    id: root

    required property QtObject lines
    required property int row
    required property string mode
    required property real pxPerSec

    target: null
    yAxis.enabled: false

    onActiveChanged: {
        if (active)
            lines.beginDrag(row)
        else
            lines.endDrag()
    }

    onActiveTranslationChanged: {
        if (active)
            lines.dragMove(row, mode, activeTranslation.x / pxPerSec)
    }
}
