import QtQuick

Text {
    property real pixelSize: 40

    font.family: "Vazirmatn FD"
    font.weight: Font.Black
    font.pixelSize: Math.max(1, pixelSize)
    horizontalAlignment: Text.AlignHCenter
    wrapMode: Text.WordWrap
}
