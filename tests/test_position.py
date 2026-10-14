"""Saved and off-screen coordinates must survive output initialization."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('PULSE_SERVER', 'unix:/tmp/desktop-cast-no-audio')
os.environ.setdefault('QT_MEDIA_BACKEND', 'ffmpeg')
import unittest
from pathlib import Path
from PySide6.QtCore import QUrl, QObject
from PySide6.QtQml import QQmlEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication

class PositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_clickthrough_position_recovers_when_screen_finishes_sizing(self):
        engine = QQmlEngine()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / 'overlays/Character.qml')))
        panel = QQuickItem()
        controller_component = QQmlComponent(engine)
        controller_component.setData(b'import QtQml; QtObject { property bool ctrlHeld: false; property string activeId: ""; function placement(character, output) { return {x:character.x, y:character.y}; } }', QUrl())
        controller = controller_component.create()
        character = {'id':'test', 'x':390, 'y':510, 'size':100, 'clickthrough':True,
                     'asset': {'width':100,'height':100,'frames':1,'directory':'/tmp','durations':[100]}}
        pet = component.createWithInitialProperties({'character':character,'controller':controller,'panel':panel})
        self.assertIsNotNone(pet, str(component.errors()))
        self.assertEqual(pet.x(), 390)
        panel.setWidth(1920); panel.setHeight(1080)
        self.application.processEvents()
        self.assertEqual((pet.x(),pet.y()), (390,510))
        pet.setProperty('character', dict(character, clickthrough=False))
        self.assertEqual((pet.x(),pet.y()), (390,510))
        pet.deleteLater()
        self.application.processEvents()

if __name__ == '__main__':
    unittest.main()
