import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ItemDelegate {
    id: root

    required property var model
    required property int index

    signal activated(int row)

    highlighted: ListView.isCurrentItem
    onClicked: activated(index)

    contentItem: RowLayout {
        spacing: 8

        Label {
            Layout.preferredWidth: 28
            text: root.index + 1
            opacity: 0.5
            horizontalAlignment: Text.AlignRight
        }
        TimeField {
            Layout.preferredWidth: 88
            seconds: root.model.start
            onCommitted: value => root.ListView.view.model.setField(root.index, "start", value)
        }
        TimeField {
            Layout.preferredWidth: 88
            seconds: root.model.end
            onCommitted: value => root.ListView.view.model.setField(root.index, "end", value)
        }
        Label {
            Layout.fillWidth: true
            text: root.model.text
            font.family: "Vazirmatn FD"
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
        }
    }
}
