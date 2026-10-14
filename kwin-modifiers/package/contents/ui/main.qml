import QtQuick
import org.kde.kwin as KWin
import "bridge" as Native

KWin.SceneEffect {
    visible: false
    delegate: Component { Item {} }
    property QtObject modifierBridge: Native.ModifierBridge {}
}
