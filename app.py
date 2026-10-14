#!/usr/bin/env python3
"""Desktop Cast: a local character library with native Wayland overlays."""
import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from store import DATA, ROOT, SUPPORTED, add_assets, change, edit_character, initialize, prepare, read, CONTROL_DEFAULTS, control_values

VERSION = (ROOT / 'VERSION').read_text().strip()
if '--version' in sys.argv:
    print(VERSION)
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == '--download':
    from steam_download import download, emit
    try:
        download(sys.argv[2])
    except Exception as error:
        emit(error=str(error))
        raise SystemExit(1)
    raise SystemExit(0)

# Overlay edits use no GUI imports or display connection.
if len(sys.argv) > 1 and sys.argv[1] == '--edit':
    identity, action, encoded = sys.argv[2:5]
    values = json.loads(encoded)
    if action == 'remove':
        change('scene', lambda d: d.update(items=[i for i in d['items'] if i['id'] != identity]))
    elif action == 'move':
        edit_character(identity, {k: max(0, int(values[k])) for k in ('x', 'y')})
    elif action == 'set':
        edit_character(identity, control_values(values))
    elif action == 'reset':
        edit_character(identity, dict(CONTROL_DEFAULTS))
    elif action == 'resize':
        edit_character(identity, {'size': max(64, min(640, int(values['size'])))})
    raise SystemExit(0)

from PySide6.QtCore import Qt, QTimer, QSize, QProcess, QProcessEnvironment, QLockFile
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QSlider, QComboBox,
    QSplitter, QMessageBox, QLineEdit, QAbstractItemView, QSizePolicy, QSystemTrayIcon, QMenu)


from tool_ui import ToolActions


class Window(ToolActions, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Desktop Cast')
        self.resize(1160, 780)
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.pending = []
        self.asset = None
        self.frame = 0
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.advance)
        self.scene_stamp = None
        from modifier_bridge import ModifierBridge
        self.modifiers = ModifierBridge(self)
        self.overlay = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert('DESKTOP_CAST_DATA', str(DATA))
        environment.insert('DESKTOP_CAST_ROOT', str(ROOT))
        environment.insert('DESKTOP_CAST_EXECUTABLE', sys.executable)
        environment.insert('DESKTOP_CAST_SCRIPT', '' if getattr(sys, 'frozen', False) else str(ROOT / 'app.py'))
        # Host Quickshell must load host Qt libraries, not the packaged Python Qt.
        if getattr(sys, 'frozen', False):
            environment.remove('QT_PLUGIN_PATH')
            environment.remove('QT_QPA_PLATFORM_PLUGIN_PATH')
            if environment.contains('LD_LIBRARY_PATH_ORIG'):
                environment.insert('LD_LIBRARY_PATH', environment.value('LD_LIBRARY_PATH_ORIG'))
            else:
                environment.remove('LD_LIBRARY_PATH')
        environment.remove('PYTHONPATH')
        environment.remove('PYTHONHOME')
        self.overlay.setProcessEnvironment(environment)
        self.overlay.setProcessChannelMode(QProcess.MergedChannels)
        self.overlay.setStandardOutputFile(str(DATA / 'overlay.log'))
        self.overlay.finished.connect(self.overlay_stopped)

        from ui import build_ui
        build_ui(self)
        self.load_library()
        self.quitting = False
        self.window_request_stamp = (DATA / 'window-request.json').stat().st_mtime_ns
        self.tray = QSystemTrayIcon(self)
        icon = QIcon(str(ROOT / 'packaging/desktop-cast.svg'))
        if icon.isNull():
            icon = QIcon(str(ROOT / 'desktop-cast.svg'))
        if icon.isNull():
            icon = QIcon.fromTheme('preferences-desktop-wallpaper')
        if icon.isNull():
            icon = self.style().standardIcon(__import__('PySide6.QtWidgets', fromlist=['QStyle']).QStyle.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray.setIcon(icon)
        self.tray.setToolTip('Desktop Cast')
        tray_menu = QMenu(self)
        tray_menu.addAction('Open Desktop Cast', self.show_window)
        tray_menu.addAction('Show / hide characters', self.toggle_visibility)
        tray_menu.addSeparator()
        tray_menu.addAction('Quit Desktop Cast', self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.tick)
        self.poll.start(250)
        self.overlay.start('quickshell', ['--path', str(ROOT / 'shell.qml'), '--no-color'])
        if not self.overlay.waitForStarted(3000):
            QMessageBox.critical(self, 'Overlay could not start', self.overlay.errorString())

    def refresh_screens(self, *_):
        previous = self.screen.currentText() if hasattr(self, 'screen') else ''
        self.screen.clear()
        self.screen.addItems([s.name() for s in QApplication.screens()])
        if previous:
            self.screen.setCurrentText(previous)

    def choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Add animations', str(Path.home()),
            'Images and animations (*.gif *.apng *.png *.webp *.jpg *.jpeg *.bmp)')
        self.queue_import(paths)

    def open_workshop(self):
        self.tabs.setCurrentIndex(1)

    def import_workshop(self):
        roots = [Path.home() / '.local/share/Steam/steamapps/workshop/content/3474900']
        # Steam library paths are local configuration, not remote downloads.
        folders = Path.home() / '.local/share/Steam/steamapps/libraryfolders.vdf'
        if folders.exists():
            import re
            roots.extend(Path(p) / 'steamapps/workshop/content/3474900'
                         for p in re.findall(r'"path"\s+"([^"]+)"', folders.read_text()))
        paths = sorted({p.resolve() for root in roots if root.exists()
                        for p in root.rglob('*') if p.suffix.lower() in SUPPORTED})
        if not paths:
            self.statusBar().showMessage('No downloaded animaEngine images found. Use Add files to choose a folder’s files.')
        self.queue_import(paths)

    def queue_import(self, paths):
        queued = {str(p) for _, p in self.pending}
        for path in paths:
            if str(path) not in queued:
                self.pending.append((self.pool.submit(prepare, path), path))
        if self.pending:
            self.statusBar().showMessage(f'Preparing {len(self.pending)} files. Large animations may take a moment…')

    def tick(self):
        request_stamp = (DATA / 'window-request.json').stat().st_mtime_ns
        if request_stamp != self.window_request_stamp:
            self.window_request_stamp = request_stamp
            self.show_window()
        self.poll_tools()
        finished = [(f, p) for f, p in self.pending if f.done()]
        if finished:
            successful, failures = [], []
            for future, path in finished:
                try:
                    successful.append(future.result())
                except Exception as error:
                    failures.append(f'{Path(path).name}: {error}')
                self.pending.remove((future, path))
            if successful:
                add_assets(successful)
                self.load_library()
            self.statusBar().showMessage(f'Preparing {len(self.pending)} files…' if self.pending else 'Library ready.')
            if failures:
                QMessageBox.warning(self, 'Some files could not be imported', '\n'.join(failures))
        stamp = (DATA / 'scene.json').stat().st_mtime_ns
        if stamp != self.scene_stamp:
            self.scene_stamp = stamp
            scene = read('scene')
            identity = getattr(self, 'select_active_id', None) or (self.active.currentItem().data(Qt.UserRole) if self.active.currentItem() else None)
            self.select_active_id = None
            self.active.clear()
            for character in scene['items']:
                item = QListWidgetItem(f"{character['asset']['name']}  •  {character['size']} px  •  {character['screen']}")
                item.setData(Qt.UserRole, character['id'])
                self.active.addItem(item)
                if identity == character['id']:
                    self.active.setCurrentItem(item)
            if self.active.count() and not self.active.currentItem():
                self.active.setCurrentRow(0)
            self.hide_button.setText('Hide characters' if scene.get('visible', True) else 'Show characters')

    def load_library(self):
        previous = self.asset['id'] if self.asset else None
        self.library.clear()
        for asset in read('library')['items']:
            thumbnail = QPixmap(str(Path(asset['directory']) / '00000.png'))
            icon = QIcon(thumbnail)
            icon.addPixmap(thumbnail, QIcon.Selected)
            item = QListWidgetItem(icon, Path(asset['name']).stem.replace('_', ' '))
            item.setData(Qt.UserRole, asset)
            item.setToolTip(asset['source'])
            self.library.addItem(item)
            if asset['id'] == previous:
                self.library.setCurrentItem(item)
        if not self.library.currentItem() and self.library.count():
            self.library.setCurrentRow(0)
        self.filter_library(self.search.text())

    def filter_library(self, text):
        for i in range(self.library.count()):
            item = self.library.item(i)
            item.setHidden(text.casefold() not in item.text().casefold())

    def select_asset(self, item, _previous):
        self.preview_timer.stop()
        self.asset = item.data(Qt.UserRole) if item else None
        self.place_button.setEnabled(self.asset is not None)
        if not self.asset:
            self.preview.clear()
            return
        self.frame = 0
        self.name.setText(Path(self.asset['name']).stem.replace('_', ' ')[:70])
        self.name.setToolTip(self.asset['name'])
        self.metadata.setText(f"{self.asset['frames']} frames   |   {self.asset['width']} × {self.asset['height']} prepared pixels")
        self.paint_preview()

    def paint_preview(self):
        if not self.asset:
            return
        pixmap = QPixmap(str(Path(self.asset['directory']) / f'{self.frame:05d}.png'))
        self.preview.setPixmap(pixmap.scaled(self.preview.size() - QSize(24, 24), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if self.asset['frames'] > 1:
            self.preview_timer.start(max(8, round(1000/self.fps.value())) if self.fps.value() else self.asset['durations'][self.frame])

    def advance(self):
        self.frame = (self.frame + 1) % self.asset['frames']
        self.paint_preview()

    def show_controls(self):
        item = self.active.currentItem()
        if not item:
            self.statusBar().showMessage('Select a running character below, or launch an animation first.')
            return
        character = next((i for i in read('scene')['items'] if i['id'] == item.data(Qt.UserRole)), None)
        if character:
            import time
            change('control-request', lambda d: d.update(id=character['id'], screen=character['screen'],
                x=character['x'] + character['size'], y=max(12, character['y'] - 120), nonce=time.time_ns()))

    def reset_all_controls(self):
        def reset(doc):
            doc['visible'] = True
            for character in doc['items']:
                character.update(CONTROL_DEFAULTS)
        change('scene', reset)
        self.statusBar().showMessage('Character controls reset. Position and library files were kept.')

    def remove_library(self):
        selected = {item.data(Qt.UserRole)['id'] for item in self.library.selectedItems()}
        if not selected: return
        change('library', lambda d: d.update(items=[i for i in d['items'] if i['id'] not in selected]))
        self.load_library()
        self.statusBar().showMessage('Removed from the library. Source files and running characters were kept.')

    def open_location(self):
        if self.asset:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.asset['source']).parent)))

    def attach_audio(self):
        item = self.active.currentItem()
        if not item:
            self.statusBar().showMessage('Select a running character before attaching audio.'); return
        path, _ = QFileDialog.getOpenFileName(self, 'Attach audio to character', str(Path.home()), 'Audio (*.mp3 *.wav *.ogg *.flac *.m4a)')
        if path: edit_character(item.data(Qt.UserRole), control_values({'audio': path}))

    def export_apng(self):
        if not self.asset: return
        path, _ = QFileDialog.getSaveFileName(self, 'Export animation', str(Path.home() / (self.asset['name'][:60] + '.apng')), 'Animated PNG (*.apng)')
        if path:
            from media_tools import export_asset
            self.tool_jobs.append((self.pool.submit(export_asset, self.asset, path), 'Animation exported', False))
            self.statusBar().showMessage('Exporting APNG…')

    def set_fps(self, value):
        if self.asset:
            self.paint_preview()
        item = self.active.currentItem()
        if item:
            character = next((i for i in read('scene')['items'] if i['id'] == item.data(Qt.UserRole)), None)
            if character and self.asset and character['asset']['id'] == self.asset['id']:
                edit_character(character['id'], {'fps': value})

    def update_size(self, value):
        self.size_label.setText(f'{value} px')
        item = self.active.currentItem()
        if item:
            edit_character(item.data(Qt.UserRole), {'size': value})

    def place(self):
        if not self.asset:
            return
        if self.overlay.state() == QProcess.NotRunning:
            QMessageBox.warning(self, 'Overlay is not running', 'Restart Desktop Cast. See .state/overlay.log for the error.')
            return
        screen = next((s for s in QApplication.screens() if s.name() == self.screen.currentText()), QApplication.primaryScreen())
        width = self.size.value()
        height = width * self.asset['height'] / self.asset['width']
        offset = (len(read('scene')['items']) % 5) * 40
        character = {'id': uuid.uuid4().hex, 'asset': self.asset, 'screen': screen.name(),
                     **CONTROL_DEFAULTS, 'size': width, 'fps': self.fps.value(), 'layer': read('scene').get('layer','overlay'), 'x': 80 + offset, 'y': max(0, screen.size().height() - height - 80)}
        change('scene', lambda d: (d['items'].append(character), d.update(visible=True)))
        self.select_active_id = character['id']
        self.statusBar().showMessage('Character placed. Drag it to move, or scroll over it to resize.')

    def remove_selected(self):
        item = self.active.currentItem()
        if item:
            identity = item.data(Qt.UserRole)
            change('scene', lambda d: d.update(items=[i for i in d['items'] if i['id'] != identity]))

    def toggle_visibility(self):
        change('scene', lambda d: d.update(visible=not d.get('visible', True)))

    def overlay_stopped(self, code, _status):
        if self.isVisible():
            self.statusBar().showMessage(f'Character overlay stopped ({code}). See .state/overlay.log.')

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self.asset:
            self.paint_preview()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window()

    def quit_app(self):
        self.quitting = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if not self.quitting and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.preview_timer.stop()
            return
        self.tray.hide()
        self.modifiers.stop()
        if hasattr(self, 'workshop_browser'):
            self.workshop_browser.close()
        self.preview_timer.stop()
        self.overlay.terminate()
        if not self.overlay.waitForFinished(2000):
            self.overlay.kill()
        self.pool.shutdown(wait=False, cancel_futures=True)
        event.accept()


def main():
    initialize()
    app = QApplication(sys.argv)
    app.setApplicationName('Desktop Cast')
    app.setApplicationVersion(VERSION)
    app.setDesktopFileName('desktop-cast')
    lock = QLockFile(str(DATA / 'app.lock'))
    if not lock.tryLock(0):
        import time
        change('window-request', lambda d: d.update(nonce=time.time_ns()))
        return 0
    change('control-request', lambda d: d.update(id='', nonce=0))
    app.setStyle('Fusion')
    app.setFont(QFont('Noto Sans', 10))
    app.setStyleSheet((ROOT / 'theme.qss').read_text())
    window = Window()
    window.show()
    def fit_window():
        available = window.windowHandle().screen().availableGeometry()
        window.resize(min(1160, available.width() - 40), min(800, available.height() - 60))
        window.move(available.center() - window.rect().center())
    QTimer.singleShot(0, fit_window)
    return app.exec()

if __name__ == '__main__':
    raise SystemExit(main())
