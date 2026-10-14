"""Exercise the same output-coordinate math used by the Wayland overlay."""
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from pathlib import Path
from PySide6.QtQml import QJSEngine
from PySide6.QtWidgets import QApplication

class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.engine = QJSEngine()
        source = Path(__file__).resolve().parents[1] / 'overlays/geometry.js'
        result = self.engine.evaluate(source.read_text())
        self.assertFalse(result.isError(), result.toString())
        self.screens = [{'name':'left','x':-1920,'y':0,'width':1920,'height':1080},
                        {'name':'main','x':0,'y':0,'width':2560,'height':1440}]

    def call(self, name, *arguments):
        encoded = ','.join(json.dumps(a) for a in arguments)
        result = self.engine.evaluate(f'JSON.stringify({name}({encoded}))')
        self.assertFalse(result.isError(), result.toString())
        return json.loads(result.toString())

    def test_sprite_spans_adjacent_monitors(self):
        character = {'id':'a','screen':'main','x':-50,'y':200}
        self.assertEqual(self.call('placement',character,self.screens,self.screens[0],{}),{'x':1870,'y':200})
        self.assertEqual(self.call('placement',character,self.screens,self.screens[1],{}),{'x':-50,'y':200})

    def test_drag_crosses_into_monitor_with_negative_global_origin(self):
        character = {'id':'a','screen':'main','x':100,'y':200}
        moved = self.call('finishMove',character,self.screens,self.screens[1],-200,300,-150,350)
        self.assertEqual(moved,{'screen':'left','x':1720,'y':300})

    def test_offscreen_position_is_preserved(self):
        character = {'id':'a','screen':'main','x':-50,'y':-30}
        self.assertEqual(self.call('placement',character,self.screens,self.screens[1],{}),{'x':-50,'y':-30})
        self.assertEqual(self.call('finishMove',character,self.screens,self.screens[1],200,-40,250,-10),
                         {'screen':'main','x':200,'y':-40})

    def test_live_drag_preview_updates_other_monitor(self):
        character = {'id':'a','screen':'main','x':100,'y':200}
        drag = {'id':'a','x':-60,'y':300}
        self.assertEqual(self.call('placement',character,self.screens,self.screens[0],drag),{'x':1860,'y':300})

if __name__ == '__main__':
    unittest.main()
