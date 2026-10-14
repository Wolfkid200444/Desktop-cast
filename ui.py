"""Anima-inspired native library, Workshop, tools, and settings pages."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QListWidget, QListView, QAbstractItemView, QSplitter, QScrollArea, QSlider,
    QSpinBox, QStackedWidget, QSizePolicy)
from store import read


def button(text, callback, kind=None):
    widget = QPushButton(text)
    if kind: widget.setObjectName(kind)
    widget.clicked.connect(callback)
    return widget


class Pages(QStackedWidget):
    """Keep navigation separate from the page container."""
    def addTab(self, widget, label):
        return self.addWidget(widget)

    def removeTab(self, index):
        self.removeWidget(self.widget(index))

    def insertTab(self, index, widget, label):
        return self.insertWidget(index, widget)


def build_ui(w):
    w.tool_jobs = []
    body = QWidget(); w.setCentralWidget(body)
    layout = QHBoxLayout(body); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
    rail = QWidget(); rail.setObjectName('sidebar'); rail.setFixedWidth(180)
    navigation = QVBoxLayout(rail); navigation.setContentsMargins(14, 22, 14, 16); navigation.setSpacing(8)
    brand = QLabel('Desktop Cast'); brand.setObjectName('brand'); navigation.addWidget(brand)
    subtitle = QLabel('Your desktop companions'); subtitle.setObjectName('muted'); navigation.addWidget(subtitle)
    navigation.addSpacing(24)
    w.tabs = Pages()
    from PySide6.QtGui import QIcon
    nav_buttons = []
    for index, (label, icon) in enumerate([('Library','view-grid'), ('Workshop','applications-internet'),
                                         ('Tools','applications-utilities'), ('Settings','configure')]):
        entry = QPushButton(label); entry.setIcon(QIcon.fromTheme(icon))
        entry.setObjectName('navigation'); entry.setCheckable(True); entry.setAutoExclusive(True)
        entry.clicked.connect(lambda checked=False, i=index: w.tabs.setCurrentIndex(i))
        navigation.addWidget(entry); nav_buttons.append(entry)
    nav_buttons[0].setChecked(True)
    w.tabs.currentChanged.connect(lambda i: nav_buttons[i].setChecked(True) if 0 <= i < len(nav_buttons) else None)
    navigation.addStretch()
    navigation.addWidget(QLabel('New characters'))
    w.layer = QComboBox(); w.layer.addItems(['Above windows', 'On desktop'])
    w.layer.setCurrentIndex(1 if read('scene').get('layer') == 'desktop' else 0)
    w.layer.currentIndexChanged.connect(lambda i: __import__('store').change('scene', lambda d: d.update(layer='desktop' if i else 'overlay')))
    navigation.addWidget(w.layer)
    w.hide_button = button('Hide characters', w.toggle_visibility); navigation.addWidget(w.hide_button)
    tray_hint = QLabel('Closing the window keeps characters running in the tray.')
    tray_hint.setObjectName('muted'); tray_hint.setWordWrap(True); navigation.addWidget(tray_hint)
    layout.addWidget(rail)
    content = QWidget(); main = QVBoxLayout(content); main.setContentsMargins(22, 18, 22, 8)
    main.addWidget(w.tabs); layout.addWidget(content, 1)
    library_page = QWidget(); page = QVBoxLayout(library_page); page.setContentsMargins(0, 0, 0, 0)
    title = QLabel('Library'); title.setObjectName('title'); page.addWidget(title)
    hint = QLabel('Select an animation to preview it. Double-click to launch it.'); hint.setObjectName('muted'); page.addWidget(hint)
    toolbar = QHBoxLayout()
    toolbar.addWidget(button('Add animation', w.choose_files, 'primary'))
    toolbar.addWidget(button('Remove selected', w.remove_library, 'danger'))
    w.search = QLineEdit(); w.search.setPlaceholderText('Search in your library…'); w.search.textChanged.connect(w.filter_library)
    toolbar.addWidget(w.search, 1); page.addLayout(toolbar)
    split = QSplitter()
    w.library = QListWidget()
    w.library.setViewMode(QListView.IconMode); w.library.setResizeMode(QListView.Adjust)
    w.library.setMovement(QListView.Static); w.library.setIconSize(QSize(140, 130))
    w.library.setGridSize(QSize(168, 178)); w.library.setSpacing(6)
    w.library.setWordWrap(True); w.library.setMinimumWidth(290)
    w.library.setSelectionMode(QAbstractItemView.ExtendedSelection)
    w.library.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    w.library.setTextElideMode(Qt.ElideMiddle)
    w.library.currentItemChanged.connect(w.select_asset)
    w.library.itemDoubleClicked.connect(lambda _: w.place())
    split.addWidget(w.library)
    side = QWidget(); detail = QVBoxLayout(side); detail.setContentsMargins(12, 0, 0, 0)
    w.preview = QLabel('Select an animation'); w.preview.setAlignment(Qt.AlignCenter)
    w.preview.setMinimumSize(200, 190); w.preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    w.preview.setObjectName('preview'); detail.addWidget(w.preview)
    w.name = QLabel('Select an animation'); w.name.setWordWrap(True)
    w.name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred); w.name.setObjectName('assetName'); detail.addWidget(w.name)
    w.metadata = QLabel('GIF, APNG, WebP and still images'); w.metadata.setObjectName('muted'); detail.addWidget(w.metadata)
    playback = QHBoxLayout(); playback.addWidget(QLabel('Playback FPS'))
    w.fps = QSpinBox(); w.fps.setRange(0, 120); w.fps.setSpecialValueText('Original'); w.fps.setValue(15); w.fps.valueChanged.connect(w.set_fps); playback.addWidget(w.fps)
    detail.addLayout(playback)
    size = QHBoxLayout(); size.addWidget(QLabel('Width'))
    w.size = QSlider(Qt.Horizontal); w.size.setRange(64,640); w.size.setValue(192); w.size.valueChanged.connect(w.update_size)
    size.addWidget(w.size,1); w.size_label = QLabel('192 px'); size.addWidget(w.size_label); detail.addLayout(size)
    w.screen = QComboBox(); w.refresh_screens(); detail.addWidget(w.screen)
    from PySide6.QtWidgets import QApplication
    QApplication.instance().screenAdded.connect(w.refresh_screens); QApplication.instance().screenRemoved.connect(w.refresh_screens)
    w.place_button = button('Launch animation',w.place,'primary'); w.place_button.setEnabled(False); detail.addWidget(w.place_button)
    detail.addWidget(QLabel('Quick actions'))
    for text, callback in [('Animation controls / Rotate / Flip',w.show_controls),('Attach audio to selected character…',w.attach_audio),
                           ('Export as APNG…',w.export_apng),('Open file location',w.open_location)]:
        detail.addWidget(button(text,callback))
    detail.addStretch()
    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(side); scroll.setMinimumWidth(255); scroll.setMaximumWidth(290)
    split.addWidget(scroll); split.setSizes([650,270]); page.addWidget(split,1)
    running = QHBoxLayout(); running.addWidget(QLabel('Running characters')); running.addStretch()
    running.addWidget(button('Controls…',w.show_controls)); running.addWidget(button('Close selected',w.remove_selected))
    running.addWidget(button('Clear desktop',lambda: __import__('store').change('scene',lambda d:d.update(items=[]))))
    page.addLayout(running)
    w.active = QListWidget(); w.active.setMaximumHeight(72); page.addWidget(w.active)
    w.tabs.addTab(library_page,'Library')
    workshop_placeholder = QWidget(); w.tabs.addTab(workshop_placeholder,'Workshop')
    def tab_changed(index):
        if index == 1 and not hasattr(w,'workshop_browser'):
            from workshop_dialog import WorkshopBrowser
            w.workshop_browser = WorkshopBrowser(w)
            w.workshop_browser.downloaded.connect(w.queue_import)
            w.tabs.removeTab(1); w.tabs.insertTab(1,w.workshop_browser,'Workshop'); w.tabs.setCurrentIndex(1)
    w.tabs.currentChanged.connect(tab_changed)
    from tool_ui import tools_page, settings_page
    w.tabs.addTab(tools_page(w),'Tools'); w.tabs.addTab(settings_page(w),'Settings')
    w.controls_shortcut = QShortcut(QKeySequence('Ctrl+E'),w)
    w.controls_shortcut.activated.connect(w.show_controls)
    w.recovery_shortcut = QShortcut(QKeySequence('Ctrl+Shift+R'),w)
    w.recovery_shortcut.activated.connect(w.reset_all_controls)
    w.statusBar().showMessage('Right-click a character for controls. Drag to move; scroll to resize.')
