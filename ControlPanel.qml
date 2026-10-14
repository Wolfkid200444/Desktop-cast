import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: menu
    required property var controller
    property var character: controller.controlItem
    property bool expanded: false
    width: 320
    height: Math.min(contentColumn.implicitHeight + 28, parent.height - 24)
    radius: 18
    color: "#101720"
    border.color: "#304154"
    component MenuButton: Button {
        id: actionButton
        property bool danger: false
        implicitHeight: 34
        background: Rectangle {
            radius: 8
            color: actionButton.down ? "#29496d" : (actionButton.danger ? "#2b1a24" : "#17263a")
            border.color: actionButton.danger ? "#78374b" : "#355575"
        }
        contentItem: Text {
            text: actionButton.text; color: "#edf3fc"; font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
    }
    component MenuCheck: CheckBox {
        id: checkControl
        implicitHeight: 30
        indicator: Rectangle {
            implicitWidth: 18; implicitHeight: 18; x: 0; y: (checkControl.height - height) / 2; radius: 4
            color: checkControl.checked ? "#64a2ff" : "#111b29"; border.color: "#547293"
            Text { anchors.centerIn: parent; text: checkControl.checked ? "✓" : ""; color: "#081321" }
        }
        contentItem: Text {
            text: checkControl.text; color: "#e6edf8"; font.pixelSize: 12
            leftPadding: 25; verticalAlignment: Text.AlignVCenter
        }
    }
    function setControl(key, value) {
        let values = {}; values[key] = value;
        controller.edit(controller.activeId, "set", values);
    }
    Dialog {
        id: accessNotice
        parent: menu
        anchors.centerIn: parent
        width: menu.width - 30
        title: "Animation access"
        modal: true
        standardButtons: Dialog.NoButton
        header: Label { text: "Animation access"; color: "#edf3fc"; font.bold: true; padding: 16 }
        footer: MenuButton { text: "OK"; onClicked: accessNotice.close() }
        background: Rectangle { color: "#172131"; radius: 12; border.color: "#3b5273" }
        contentItem: Label {
            text: "Click-through sends mouse clicks to the app behind this character.\n\nHold Ctrl and right-click the character to reopen its menu on KDE. You can also select it in Desktop Cast and press Ctrl+E.\n\nTo reset all character controls, focus Desktop Cast and press Ctrl+Shift+R."
            color: "#e6edf8"
            wrapMode: Text.WordWrap
        }
    }
    MouseArea { anchors.fill: parent }
    ScrollView {
        anchors.fill: parent; anchors.margins: 14
        clip: true
        contentWidth: availableWidth
        ColumnLayout {
            id: contentColumn
            width: menu.width - 28
            spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Label { text: menu.expanded ? "Edit live animation" : "Animation controls"; color: "#f1f4fa"; font.pixelSize: 17; font.bold: true; Layout.fillWidth: true }

            }
            Label { text: menu.expanded ? "Changes apply to the running character." : "Choose how this character behaves."; color: "#a3b0c2"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Repeater {
                model: [
                    {key:"layer", title:"Keep above other windows", hint:"Show above normal windows."},
                    {key:"locked", title:"Lock position", hint:"Prevent accidental dragging."},
                    {key:"clickthrough", title:"Click-through", hint:controller.modifierAvailable ? "Hold Ctrl and right-click to open controls." : "Edit this character from Desktop Cast."},
                    {key:"hide_cursor", title:"Hide under cursor", hint:"Hide the image while the pointer is over it."}
                ]
                delegate: Rectangle {
                    required property var modelData
                    visible: !menu.expanded
                    Layout.fillWidth: true; implicitHeight: 52; radius: 12
                    color: "#171f2a"; border.color: "#2b3a4d"
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 9
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 4
                            Label { text: modelData.title; color: "#e6edf8"; font.pixelSize: 12 }
                            Label { text: modelData.hint; color: "#a2b0c3"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                        Switch {
                            id: toggle
                            implicitWidth: 44; implicitHeight: 28
                            indicator: Rectangle {
                                implicitWidth: 42; implicitHeight: 24; radius: 12
                                x: (toggle.width - width) / 2; y: (toggle.height - height) / 2
                                color: toggle.checked ? "#64a2ff" : "#0d1723"
                                border.color: toggle.checked ? "#64a2ff" : "#49627f"
                                Rectangle {
                                    width: 18; height: 18; radius: 9; y: 3
                                    x: toggle.checked ? parent.width - width - 3 : 3
                                    color: toggle.checked ? "#f2f6ff" : "#6d829b"
                                }
                            }
                            checked: modelData.key === "layer" ? (menu.character.layer || controller.scene.layer || "overlay") === "overlay" : !!menu.character[modelData.key]
                            onClicked: {
                                menu.setControl(modelData.key, modelData.key === "layer" ? (checked ? "overlay" : "desktop") : checked);
                                if (modelData.key === "clickthrough" && checked) accessNotice.open();
                            }
                        }
                    }
                }
            }
            MenuButton {
                text: menu.expanded ? "← Back to animation controls" : "Edit live animation… ▸"
                Layout.fillWidth: true
                onClicked: menu.expanded = !menu.expanded
            }
            ColumnLayout {
                visible: menu.expanded
                Layout.fillWidth: true
                spacing: 6
            RowLayout {
                Label { text: "Width"; color: "#aab8cb"; Layout.preferredWidth: 60 }
                Slider {
                    Layout.fillWidth: true; from: 64; to: 640; stepSize: 8
                    value: menu.character.size || 192
                    onPressedChanged: if (!pressed) menu.setControl("size", Math.round(value))
                }
                Label { text: (menu.character.size || 192) + " px"; color: "#e6edf8" }
            }
            RowLayout {
                Label { text: "FPS"; color: "#aab8cb"; Layout.preferredWidth: 60 }
                SpinBox {
                    from: 0; to: 120; value: menu.character.fps === undefined ? 15 : menu.character.fps
                    palette.text: "#e6edf8"; palette.buttonText: "#e6edf8"
                    background: Rectangle { color: "#101d2d"; radius: 6; border.color: "#355575" }
                    onValueModified: menu.setControl("fps", value)
                }
                Label { text: "0 = original timing"; color: "#aab8cb"; font.pixelSize: 10 }
            }
            RowLayout {
                Label { text: "Rotate"; color: "#aab8cb"; Layout.preferredWidth: 60 }
                Slider {
                    Layout.fillWidth: true; from: -180; to: 180; stepSize: 5
                    value: menu.character.rotation || 0
                    onPressedChanged: if (!pressed) menu.setControl("rotation", Math.round(value))
                }
                Label { text: (menu.character.rotation || 0) + "°"; color: "#e6edf8" }
            }
            RowLayout {
                MenuCheck { text: "Flip horizontal"; checked: !!menu.character.flip_x; onClicked: menu.setControl("flip_x", checked) }
                MenuCheck { text: "Flip vertical"; checked: !!menu.character.flip_y; onClicked: menu.setControl("flip_y", checked) }
            }
                MenuCheck { text: "Pause animation"; checked: !!menu.character.paused; onClicked: menu.setControl("paused", checked) }
            }
            Label { text: controller.modifierAvailable ? "Hold Ctrl + right-click to open this menu, even in click-through mode." : "Select a running character in Desktop Cast and press Ctrl+E."; color: "#8f9fb5"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
            RowLayout {
                Layout.fillWidth: true
                MenuButton { text: "Reset controls"; Layout.fillWidth: true; onClicked: controller.edit(controller.activeId, "reset", {}) }
                MenuButton {
                    danger: true
                    text: "Close animation"; Layout.fillWidth: true
                    onClicked: { controller.edit(controller.activeId, "remove", {}); controller.activeId = ""; }
                }
            }
        }
    }
}
