import QtQuick
import QtMultimedia

Item {
    id: pet
    required property var character
    required property var controller
    required property var panel
    property var asset: character.asset
    property int frame: 0
    property real baseWidth: character.size
    property real baseHeight: baseWidth * asset.height / asset.width
    property real angle: (character.rotation || 0) * Math.PI / 180
    width: Math.abs(baseWidth * Math.cos(angle)) + Math.abs(baseHeight * Math.sin(angle))
    height: Math.abs(baseWidth * Math.sin(angle)) + Math.abs(baseHeight * Math.cos(angle))
    x: Math.max(0, Math.min(panel.width - width, character.x))
    y: Math.max(0, Math.min(panel.height - height, character.y))
    Image {
        anchors.centerIn: parent
        width: pet.baseWidth; height: pet.baseHeight
        source: "file://" + pet.asset.directory + "/" + String(pet.frame).padStart(5, "0") + ".png"
        fillMode: Image.PreserveAspectFit
        rotation: pet.character.rotation || 0
        transform: Scale {
            origin.x: pet.baseWidth / 2; origin.y: pet.baseHeight / 2
            xScale: pet.character.flip_x ? -1 : 1
            yScale: pet.character.flip_y ? -1 : 1
        }
        opacity: pet.character.hide_cursor && mouse.containsMouse && !controller.ctrlHeld && controller.activeId !== pet.character.id ? 0 : 1
        smooth: true
    }
    Timer {
        interval: pet.character.fps > 0 ? Math.max(8, Math.round(1000 / pet.character.fps)) : (pet.asset.durations[pet.frame] || 100)
        running: panel.visible && !pet.character.paused && pet.asset.frames > 1
        repeat: true
        onTriggered: pet.frame = (pet.frame + 1) % pet.asset.frames
    }
    MediaPlayer {
        id: sound
        source: pet.character.audio ? "file://" + pet.character.audio : ""
        loops: MediaPlayer.Infinite
        audioOutput: AudioOutput { volume: pet.character.volume === undefined ? 0.7 : pet.character.volume }
        function sync() {
            if (!source.toString()) return;
            if (panel.visible && !pet.character.paused) play(); else pause();
        }
        Component.onCompleted: sync()
        onSourceChanged: sync()
    }
    Connections { target: panel; function onVisibleChanged() { sound.sync(); } }
    onCharacterChanged: {
        if (sound) sound.sync();
        if (panel && character && !mouse.drag.active) {
            x = Qt.binding(() => Math.max(0, Math.min(panel.width - width, character.x)));
            y = Qt.binding(() => Math.max(0, Math.min(panel.height - height, character.y)));
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: !pet.character.clickthrough || controller.ctrlHeld
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        drag.target: !pet.character.locked && pressedButtons === Qt.LeftButton ? pet : null
        drag.minimumX: 0; drag.maximumX: Math.max(0, panel.width - pet.width)
        drag.minimumY: 0; drag.maximumY: Math.max(0, panel.height - pet.height)
        cursorShape: pet.character.locked ? Qt.ArrowCursor : (pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
        onReleased: event => {
            if (event.button === Qt.RightButton)
                controller.openControls(pet.character.id, panel.screen.name, pet.x + event.x, pet.y + event.y);
            else if (!pet.character.locked)
                controller.edit(pet.character.id, "move", {x: Math.round(pet.x), y: Math.round(pet.y)});
        }
        onWheel: wheel => {
            controller.edit(pet.character.id, "set", {size: Math.max(64, Math.min(640, pet.baseWidth + (wheel.angleDelta.y > 0 ? 16 : -16)))});
            wheel.accepted = true;
        }
    }
}
