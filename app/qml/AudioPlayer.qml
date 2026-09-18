import QtQuick
import QtMultimedia

MediaPlayer {
    id: root

    required property QtObject backend
    readonly property bool playing: playbackState === MediaPlayer.PlayingState

    function toggle() {
        if (playing)
            pause()
        else
            play()
    }

    source: backend.audioUrl
    audioOutput: AudioOutput {}

    onPlayingChanged: backend.playing = playing

    // Drive the shared cursor from the audio clock every frame while playing.
    readonly property FrameAnimation ticker: FrameAnimation {
        running: root.playing
        onTriggered: root.backend.requestPreview(root.position / 1000)
    }

    // backend.previewTime is the single cursor: any seek elsewhere moves the player too.
    readonly property Connections seekSync: Connections {
        target: root.backend
        function onPreviewChanged() {
            const t = root.backend.previewTime * 1000
            if (Math.abs(t - root.position) > 250)
                root.setPosition(t)
        }
    }
}
