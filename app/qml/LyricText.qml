import QtQuick

Text {
    property real pixelSize: 40
    property string family: "Vazirmatn FD"
    property int weight: Font.Black

    font.family: family
    font.weight: weight
    font.pixelSize: Math.max(1, pixelSize)
    horizontalAlignment: Text.AlignHCenter
    wrapMode: Text.WordWrap
}
