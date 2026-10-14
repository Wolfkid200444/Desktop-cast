import QtQuick
import QtQml
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

ShellRoot {
    id: shell
    property var scene: ({items: [], visible: true})
    property bool ctrlHeld: false
    property bool modifierAvailable: false
    property string activeId: ""
    property string controlScreen: ""
    property real controlX: 100
    property real controlY: 100
    property real requestNonce: 0
    property var queue: []
    readonly property var controlItem: scene.items.find(item => item.id === activeId) || ({})
    function openControls(identity, screenName, x, y) {
        activeId = identity; controlScreen = screenName; controlX = x; controlY = y;
    }
    function edit(identity, action, values) {
        let command = [Quickshell.env("DESKTOP_CAST_EXECUTABLE") || "/usr/bin/python3"];
        const script = Quickshell.env("DESKTOP_CAST_SCRIPT");
        if (script) command.push(script);
        command.push("--edit", identity, action, JSON.stringify(values));
        queue.push(command);
        drain();
    }
    function drain() {
        if (!writer.running && queue.length > 0) {
            writer.command = queue.shift(); writer.running = true;
        }
    }
    Process { id: writer; onExited: Qt.callLater(shell.drain) }
    FileView {
        path: Quickshell.env("DESKTOP_CAST_DATA") + "/scene.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try { shell.scene = JSON.parse(text()); }
            catch (error) { console.error("Cannot read character scene:", error); }
        }
    }
    FileView {
        path: Quickshell.env("DESKTOP_CAST_DATA") + "/control-request.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try {
                const request = JSON.parse(text());
                if (request.nonce > shell.requestNonce) {
                    shell.requestNonce = request.nonce;
                    if (request.id) shell.openControls(request.id, request.screen, request.x || 100, request.y || 100);
                }
            } catch (error) { console.error(error); }
        }
    }
    FileView {
        path: Quickshell.env("DESKTOP_CAST_DATA") + "/modifiers.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try {
                const state = JSON.parse(text());
                shell.modifierAvailable = !!state.available;
                shell.ctrlHeld = !!state.held && !!state.available;
            } catch (error) { console.error(error); }
        }
    }
    Variants {
        model: Quickshell.screens
        Scope {
            id: output
            required property var modelData
            Variants {
                model: ["overlay", "desktop"]
                PanelWindow {
                    id: characterWindow
                    required property var modelData
                    screen: output.modelData
                    color: "transparent"
                    visible: shell.scene.visible && characters.count > 0
                    anchors { left: true; right: true; top: true; bottom: true }
                    exclusionMode: ExclusionMode.Ignore
                    WlrLayershell.namespace: "desktop-cast-" + modelData
                    WlrLayershell.layer: modelData === "desktop" ? WlrLayer.Bottom : WlrLayer.Overlay
                    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
                    ListModel {
                        id: characterModel
                        dynamicRoles: true
                        function sync() {
                            const incoming = shell.scene.items.filter(item => item.screen === output.modelData.name && (item.layer || shell.scene.layer || "overlay") === characterWindow.modelData);
                            for (let i = count - 1; i >= 0; i--) {
                                if (!incoming.some(item => item.id === get(i).characterData.id)) remove(i);
                            }
                            for (const item of incoming) {
                                let found = -1;
                                for (let i = 0; i < count; i++) if (get(i).characterData.id === item.id) { found = i; break; }
                                if (found < 0) append({characterData: item});
                                else set(found, {characterData: item});
                            }
                        }
                        Component.onCompleted: sync()
                    }
                    Connections { target: shell; function onSceneChanged() { characterModel.sync(); } }
                    Repeater {
                        id: characters
                        model: characterModel
                        delegate: Character {
                            required property var characterData
                            character: characterData
                            controller: shell
                            panel: characterWindow
                        }
                    }
                    Instantiator {
                        id: hitRegions
                        model: characters.count
                        delegate: Region {
                            property var pet: characters.itemAt(index)
                            item: pet && (!pet.character.clickthrough || shell.ctrlHeld) ? pet : null
                        }
                    }
                    mask: Region {
                        regions: {
                            let result = [];
                            for (let i = 0; i < hitRegions.count; i++) {
                                const region = hitRegions.objectAt(i);
                                if (region) result.push(region);
                            }
                            return result;
                        }
                    }
                }
            }
            PanelWindow {
                id: controlsWindow
                screen: output.modelData
                visible: shell.activeId !== "" && shell.controlItem.id !== undefined && shell.controlScreen === output.modelData.name
                color: "transparent"
                anchors { left: true; right: true; top: true; bottom: true }
                exclusionMode: ExclusionMode.Ignore
                WlrLayershell.namespace: "desktop-cast-controls"
                WlrLayershell.layer: WlrLayer.Overlay
                WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
                MouseArea { anchors.fill: parent; onPressed: shell.activeId = "" }
                ControlPanel {
                    id: controls
                    controller: shell
                    x: Math.max(12, Math.min(parent.width - width - 12, shell.controlX))
                    y: Math.max(12, Math.min(parent.height - height - 12, shell.controlY))
                }

            }
        }
    }
}
