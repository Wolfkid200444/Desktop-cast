"""Workshop browsing and Steam download UI, separate from local playback."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QTimer, QProcess, QProcessEnvironment, QUrl, Signal
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox, QListWidget, QListWidgetItem, QLabel, QProgressBar, QMessageBox, QListView)
from .store import ROOT
from .workshop import browse, thumbnail


class WorkshopBrowser(QWidget):
    downloaded = Signal(list)

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Workshop — Desktop Cast')
        self.resize(940, 700)
        self.pool = ThreadPoolExecutor(max_workers=3)
        self.query = None
        self.thumbnails = []
        self.page = 1
        self.pages = 1
        self.files_received = False
        self.shutting_down = False
        self.download_error = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        title = QLabel('animaEngine Workshop')
        title.setObjectName('title')
        layout.addWidget(title)
        layout.addWidget(QLabel('Browse community animations. Steam handles downloads; Desktop Cast plays the images.'))
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search characters, or paste a Steam Workshop URL / item ID')
        self.search.returnPressed.connect(self.new_search)
        search_row.addWidget(self.search, 1)
        self.sort = QComboBox()
        for title, value in [('Popular this week', 'trend'), ('Top rated', 'toprated'), ('Newest', 'mostrecent')]:
            self.sort.addItem(title, value)
        self.sort.currentIndexChanged.connect(self.new_search)
        search_row.addWidget(self.sort)
        self.search_button = QPushButton('Search')
        self.search_button.clicked.connect(self.new_search)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)
        self.items = QListWidget()
        self.items.setViewMode(QListView.IconMode)
        self.items.setResizeMode(QListView.Adjust)
        self.items.setMovement(QListView.Static)
        self.items.setIconSize(QSize(160, 116))
        self.items.setGridSize(QSize(210, 178))
        self.items.setWordWrap(True)
        self.items.setSpacing(6)
        self.items.currentItemChanged.connect(self.selection_changed)
        layout.addWidget(self.items, 1)
        self.description = QLabel('Select an animation to download it into your library.')
        self.description.setWordWrap(True)
        self.description.setTextFormat(Qt.PlainText)
        layout.addWidget(self.description)
        navigation = QHBoxLayout()
        self.previous = QPushButton('Previous')
        self.previous.clicked.connect(lambda: self.change_page(-1))
        navigation.addWidget(self.previous)
        self.page_label = QLabel('Loading…')
        navigation.addWidget(self.page_label)
        self.next = QPushButton('Next')
        self.next.clicked.connect(lambda: self.change_page(1))
        navigation.addWidget(self.next)
        navigation.addStretch()
        self.open_button = QPushButton('Open item in Steam')
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_steam)
        navigation.addWidget(self.open_button)
        self.download_button = QPushButton('Download and add to library')
        self.download_button.setObjectName('primary')
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download)
        navigation.addWidget(self.download_button)
        layout.addLayout(navigation)
        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = QLabel('Connecting to Steam Community…')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        self.process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        environment.remove('PYTHONPATH'); environment.remove('PYTHONHOME')
        self.process.setProcessEnvironment(environment)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_progress)
        self.process.finished.connect(self.download_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.tick)
        self.poll.start(120)
        self.load()

    def new_search(self, *_):
        self.page = 1
        self.load()

    def change_page(self, difference):
        self.page = max(1, min(self.pages, self.page + difference))
        self.load()

    def load(self):
        if self.query:
            self.query.cancel()
        self.items.clear()
        self.thumbnails.clear()
        self.previous.setEnabled(False); self.next.setEnabled(False)
        self.page_label.setText('Loading…')
        self.status.setText('Loading Workshop results…')
        self.query = self.pool.submit(browse, self.search.text().strip(), self.sort.currentData(), self.page)

    def tick(self):
        if self.query and self.query.done():
            query, self.query = self.query, None
            try:
                result = query.result()
                self.pages = max(1, int(result.get('total_pages', 1)))
                self.page = int(result.get('current_page', self.page))
                self.page_label.setText(f'Page {self.page} of {self.pages}')
                self.previous.setEnabled(self.page > 1)
                self.next.setEnabled(self.page < self.pages)
                self.status.setText(f"{result.get('total_count', len(result['results'])):,} Workshop items. Steam must be running to download.")
                for metadata in result['results']:
                    item = QListWidgetItem(metadata['title'])
                    item.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
                    item.setData(Qt.UserRole, metadata)
                    item.setToolTip(metadata['title'])
                    self.items.addItem(item)
                    if metadata['preview']:
                        self.thumbnails.append((self.pool.submit(thumbnail, metadata['preview']), item))
                if self.items.count(): self.items.setCurrentRow(0)
                else: self.description.setText('No matches. Try another search.')
            except Exception as error:
                self.page_label.setText('Unavailable')
                self.status.setText(f'Could not load Workshop: {error}. Press Search to retry.')
        for future, item in list(self.thumbnails):
            if future.done():
                self.thumbnails.remove((future, item))
                try:
                    path = future.result()
                    if path: item.setIcon(QIcon(path))
                except Exception:
                    pass  # A missing preview does not prevent item downloads.

    def selection_changed(self, item, _previous):
        ready = item is not None
        self.open_button.setEnabled(ready)
        self.download_button.setEnabled(ready and self.process.state() == QProcess.NotRunning)
        if item:
            metadata = item.data(Qt.UserRole)
            self.description.setText(f"{metadata['title']}   |   {metadata['bytes'] / 1048576:.1f} MB")

    def open_steam(self):
        item = self.items.currentItem()
        if item:
            QDesktopServices.openUrl(QUrl('steam://url/CommunityFilePage/' + item.data(Qt.UserRole)['id']))

    def download(self):
        item = self.items.currentItem()
        if not item: return
        metadata = item.data(Qt.UserRole)
        self.files_received = False; self.download_error = None
        self.download_button.setEnabled(False)
        self.progress.setRange(0, 0); self.progress.show()
        self.status.setText('Asking Steam to download ' + metadata['title'] + '…')
        import sys
        if getattr(sys, 'frozen', False):
            self.process.start(sys.executable, ['--download', metadata['id']])
        else:
            self.process.start(sys.executable, [str(ROOT / 'app.py'), '--download', metadata['id']])

    def read_progress(self):
        while self.process.canReadLine():
            line = bytes(self.process.readLine()).decode(errors='replace').strip()
            if not line.startswith('DESKTOP_CAST '): continue
            try: update = json.loads(line[len('DESKTOP_CAST '):])
            except ValueError: continue
            if 'error' in update:
                self.download_error = update['error']
            elif 'files' in update:
                self.files_received = True
                self.downloaded.emit(update['files'])
                self.status.setText(f"Downloaded {len(update['files'])} image files. Preparing them in your library…")
                self.progress.setRange(0, 100); self.progress.setValue(100)
            elif update.get('total', 0) > 0:
                self.progress.setRange(0, 100)
                self.progress.setValue(min(100, int(update['progress'] * 100 / update['total'])))
                self.status.setText(f"Downloading through Steam: {update['progress']/1048576:.1f} / {update['total']/1048576:.1f} MB")

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.download_error = self.process.errorString()
            self.status.setText('Download could not start: ' + self.download_error)
            self.progress.hide()
            self.download_button.setEnabled(self.items.currentItem() is not None)

    def download_finished(self, code, _status):
        if self.shutting_down: return
        self.read_progress()
        self.download_button.setEnabled(self.items.currentItem() is not None)
        if code != 0 or not self.files_received:
            message = self.download_error or 'Steam did not return the downloaded files. Check Steam’s Downloads page and try again.'
            self.status.setText(message)
            self.progress.hide()
            QMessageBox.warning(self, 'Workshop download', message)

    def closeEvent(self, event):
        self.shutting_down = True
        self.poll.stop()
        if self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1000): self.process.kill()
        self.pool.shutdown(wait=False, cancel_futures=True)
        event.accept()
