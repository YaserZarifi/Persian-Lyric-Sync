import QtQuick
import QtQuick.Controls
import "time.js" as Time

TextField {
    id: root

    required property real seconds

    signal committed(string value)

    text: Time.format(seconds)
    selectByMouse: true
    horizontalAlignment: Text.AlignHCenter
    inputMethodHints: Qt.ImhFormattedNumbersOnly

    onEditingFinished: {
        committed(text)
        // Re-sync with the model in case the input was rejected or unchanged.
        text = Qt.binding(() => Time.format(root.seconds))
    }
}
