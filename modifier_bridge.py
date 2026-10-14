"""Session-local KWin Ctrl modifier integration; no key text is captured."""
from pathlib import Path
import re
from PySide6.QtCore import QObject, Slot, SLOT
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage, QDBusServiceWatcher
from store import change

SERVICE = 'org.desktopcast.Modifiers'
PATH = '/Modifiers'
INTERFACE = SERVICE
EFFECT = 'desktopcast-modifiers'


class ModifierBridge(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.closed = False
        self.owns_effect = False
        self.available = False
        self.bus = QDBusConnection.sessionBus()
        self.effects = QDBusInterface('org.kde.KWin', '/Effects', 'org.kde.kwin.Effects', self.bus)
        change('modifiers', lambda d: d.update(held=False, available=False))
        if not self.effects.isValid(): return
        # This native helper links KWin's installed headers. Rebuild after KWin updates.
        version_file = Path.home() / '.local/share/kwin/effects' / EFFECT / 'kwin-version.txt'
        system_version = Path('/usr/lib/cmake/KWin/KWinConfigVersion.cmake')
        try:
            match = re.search(r'set\(PACKAGE_VERSION "([^"]+)"\)', system_version.read_text())
            if not match or version_file.read_text().strip() != match.group(1): return
            kwin = QDBusInterface('org.kde.KWin', '/KWin', 'org.kde.KWin', self.bus)
            support = kwin.call('supportInformation')
            if support.type() == QDBusMessage.ErrorMessage or not support.arguments(): return
            runtime = re.search(r'KWin version:\s*(\S+)', str(support.arguments()[0]))
            if not runtime or runtime.group(1) != match.group(1): return
        except OSError: return
        already = self.bus.interface().isServiceRegistered(SERVICE).value()
        if not already:
            reply = self.effects.call('loadEffect', EFFECT)
            self.owns_effect = reply.type() != QDBusMessage.ErrorMessage and bool(reply.arguments() and reply.arguments()[0])
        if not self.bus.interface().isServiceRegistered(SERVICE).value(): return
        self.available = self.bus.connect(SERVICE, PATH, INTERFACE, 'controlChanged', self, SLOT('set_control(bool)'))
        if self.available:
            properties = QDBusInterface(SERVICE, PATH, 'org.freedesktop.DBus.Properties', self.bus)
            reply = properties.call('Get', INTERFACE, 'controlHeld')
            held = reply.arguments()[0] if reply.type() != QDBusMessage.ErrorMessage and reply.arguments() else False
            if hasattr(held, 'variant'): held = held.variant()
            self.set_control(bool(held))
        self.watcher = QDBusServiceWatcher(SERVICE, self.bus, QDBusServiceWatcher.WatchForUnregistration, self)
        self.watcher.serviceUnregistered.connect(self.disconnected)

    @Slot(bool)
    def set_control(self, held):
        if not self.closed:
            change('modifiers', lambda d: d.update(held=held, available=self.available))

    @Slot(str)
    def disconnected(self, _service):
        self.available = False
        self.set_control(False)

    def stop(self):
        self.closed = True
        change('modifiers', lambda d: d.update(held=False, available=False))
        if self.owns_effect:
            self.effects.call('unloadEffect', EFFECT)
