// SPDX-License-Identifier: GPL-3.0-or-later
// Exposes only Ctrl's held/released state, never key codes or typed text.
#include <input.h>
#include <QDBusConnection>
#include <QQmlExtensionPlugin>
#include <qqml.h>

class ModifierBridge : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.desktopcast.Modifiers")
    Q_PROPERTY(bool controlHeld READ controlHeld NOTIFY controlChanged)
public:
    explicit ModifierBridge(QObject *parent = nullptr) : QObject(parent)
    {
        auto *input = KWin::input();
        if (!input) return;
        m_held = input->keyboardModifiers().testFlag(Qt::ControlModifier);
        auto bus = QDBusConnection::sessionBus();
        m_owner = bus.registerService(QStringLiteral("org.desktopcast.Modifiers"));
        if (m_owner) bus.registerObject(QStringLiteral("/Modifiers"), this,
                                      QDBusConnection::ExportAllProperties | QDBusConnection::ExportAllSignals);
        connect(input, &KWin::InputRedirection::keyboardModifiersChanged, this,
                [this](Qt::KeyboardModifiers current, Qt::KeyboardModifiers) {
                    const bool held = current.testFlag(Qt::ControlModifier);
                    if (held == m_held) return;
                    m_held = held;
                    Q_EMIT controlChanged(m_held);
                });
    }
    ~ModifierBridge() override
    {
        if (m_owner) {
            auto bus = QDBusConnection::sessionBus();
            bus.unregisterObject(QStringLiteral("/Modifiers"));
            bus.unregisterService(QStringLiteral("org.desktopcast.Modifiers"));
        }
    }
    bool controlHeld() const { return m_held; }
Q_SIGNALS:
    void controlChanged(bool held);
private:
    bool m_held = false;
    bool m_owner = false;
};

class BridgePlugin : public QQmlExtensionPlugin
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)
public:
    void registerTypes(const char *uri) override
    {
        qmlRegisterType<ModifierBridge>(uri, 1, 0, "ModifierBridge");
    }
};
#include "bridge.moc"
