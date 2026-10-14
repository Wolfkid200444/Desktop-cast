"""Tools and settings pages and asynchronous creator actions."""
import uuid
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QColorDialog, QInputDialog, QFileDialog, QMessageBox)
from .store import DATA, read, change


class ToolActions:
    def poll_tools(self):
        for future, message, import_output in list(self.tool_jobs):
            if not future.done(): continue
            self.tool_jobs.remove((future,message,import_output))
            try:
                paths=future.result()
                self.statusBar().showMessage(message)
                if import_output: self.queue_import(paths)
            except Exception as error:
                QMessageBox.warning(self,'Media tool',str(error))

    def remove_background(self):
        if not self.asset:
            self.statusBar().showMessage('Select an animation in Library first.'); return
        color=QColorDialog.getColor(parent=self,title='Choose the solid background color to remove')
        if not color.isValid(): return
        tolerance,ok=QInputDialog.getInt(self,'Color tolerance','Color tolerance, 0 for exact matching:',20,0,255)
        if not ok:return
        from .media_tools import export_asset
        folder=DATA/'exports'; folder.mkdir(exist_ok=True)
        target=folder/(self.asset['name'][:50]+'-transparent-'+uuid.uuid4().hex[:6]+'.apng')
        self.tool_jobs.append((self.pool.submit(export_asset,self.asset,target,(color.red(),color.green(),color.blue()),tolerance),
                               'Background removed. Adding the new animation…',True))
        self.statusBar().showMessage('Removing the selected background color…')

    def convert_video(self):
        source,_=QFileDialog.getOpenFileName(self,'Choose a video',str(Path.home()),'Video (*.mp4 *.webm *.mov *.mkv *.avi)')
        if not source:return
        seconds,ok=QInputDialog.getInt(self,'Video segment','Convert the first how many seconds? 10 FPS, up to 320 pixels.',10,1,60)
        if not ok:return
        from .media_tools import convert_video
        self.tool_jobs.append((self.pool.submit(convert_video,source,seconds),'Video converted. Adding the animation…',True))
        self.statusBar().showMessage('Converting video to APNG…')


def action_row(title,description,callback):
    row=QWidget(); row.setStyleSheet('QWidget { background: #303030; border-radius: 6px; }')
    layout=QHBoxLayout(row); layout.setContentsMargins(18,16,18,16)
    words=QVBoxLayout(); heading=QLabel(title); heading.setStyleSheet('font-weight: 600;'); words.addWidget(heading)
    hint=QLabel(description);hint.setObjectName('muted');hint.setWordWrap(True);words.addWidget(hint)
    layout.addLayout(words,1);button=QPushButton('Open');button.clicked.connect(callback);layout.addWidget(button)
    return row


def tools_page(w):
    page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(4,20,4,20);layout.setSpacing(14)
    title=QLabel('Tools');title.setObjectName('title');layout.addWidget(title)
    description=QLabel('Prepare media for your library. Every tool keeps the source file intact.');description.setObjectName('muted');layout.addWidget(description)
    layout.addWidget(action_row('Remove background by color','Remove a solid color from the animation selected in Library.',w.remove_background))
    layout.addWidget(action_row('Convert video to animation','Convert a selected video segment into an APNG and add it to the library.',w.convert_video))
    layout.addWidget(action_row('Export GIF / WebP as APNG','Export the selected library animation with transparency and frame timing.',w.export_apng))
    layout.addWidget(action_row('Sync downloaded Workshop items','Import supported image files already downloaded by Steam.',w.import_workshop))
    layout.addStretch();return page


def settings_page(w):
    page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(4,20,4,20);layout.setSpacing(14)
    title=QLabel('Settings');title.setObjectName('title');layout.addWidget(title)
    layout.addWidget(action_row('Recover character controls','Reset locks, click-through, hover hiding, speed and orientation. Shortcut: Ctrl+Shift+R while this app is focused.',w.reset_all_controls))
    layout.addWidget(action_row('Data and cache folder','Library data and prepared frames stay in this folder.',lambda: open_folder(DATA)))
    layout.addWidget(QLabel('Hold Ctrl and right-click a character to open its controls, even in click-through mode.'))
    layout.addWidget(QLabel('KWin Ctrl recovery: ' + ('available' if w.modifiers.available else 'unavailable; use Controls… or Ctrl+E in this app.')))
    note=QLabel('Closing the window keeps characters running in the system tray. Use Quit Desktop Cast to stop them.\nWorkshop downloads require Steam to be running and signed in.\nAI background removal and Workshop publishing are not included.')
    note.setWordWrap(True);note.setObjectName('muted');layout.addWidget(note)
    layout.addWidget(action_row('Quit Desktop Cast', 'Stop all characters and exit the background app.', w.quit_app))
    layout.addStretch();return page


def open_folder(path):
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
