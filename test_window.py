"""Window close must preserve the running overlay when the tray is available."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import Mock, patch
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow
from app import Window

class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def make_window(self):
        window = Window.__new__(Window)
        QMainWindow.__init__(window)
        window.quitting = False
        window.preview_timer = Mock()
        window.modifiers = Mock()
        window.overlay = Mock()
        window.pool = Mock()
        window.tray = Mock()
        return window

    def test_close_to_tray_keeps_overlay_running(self):
        window = self.make_window()
        window.show()
        event = QCloseEvent()
        with patch('app.QSystemTrayIcon.isSystemTrayAvailable', return_value=True):
            window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.assertFalse(window.isVisible())
        window.preview_timer.stop.assert_called_once()
        window.overlay.terminate.assert_not_called()
        window.modifiers.stop.assert_not_called()

    def test_no_tray_closes_cleanly(self):
        window = self.make_window()
        event = QCloseEvent()
        with patch('app.QSystemTrayIcon.isSystemTrayAvailable', return_value=False):
            window.closeEvent(event)
        self.assertTrue(event.isAccepted())
        window.overlay.terminate.assert_called_once()
        window.modifiers.stop.assert_called_once()
        window.pool.shutdown.assert_called_once()

if __name__ == '__main__':
    unittest.main()
