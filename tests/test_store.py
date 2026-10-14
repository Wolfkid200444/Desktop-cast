import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from PIL import Image

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ['DESKTOP_CAST_DATA'] = self.temp.name
        from desktop_cast import store
        self.store = importlib.reload(store)
        self.store.initialize()

    def tearDown(self):
        self.temp.cleanup()
        os.environ.pop('DESKTOP_CAST_DATA', None)

    def test_animation_alpha_timing_cache_and_atomic_scene(self):
        path = Path(self.temp.name) / 'sample.apng'
        frames = [Image.new('RGBA', (900, 600), (200, 50, 80, 0)),
                  Image.new('RGBA', (900, 600), (50, 200, 80, 128))]
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=[40, 120], loop=0)
        asset = self.store.prepare(path)
        self.assertEqual(asset['frames'], 2)
        self.assertEqual(asset['durations'], [40, 120])
        self.assertEqual(asset['width'], 512)
        with Image.open(Path(asset['directory']) / '00001.png') as frame:
            self.assertEqual(frame.mode, 'RGBA')
            self.assertEqual(frame.getpixel((100, 100))[3], 128)
        self.assertEqual(self.store.prepare(path), asset)
        self.store.add_assets([asset]); self.store.add_assets([asset])
        self.assertEqual(len(self.store.read('library')['items']), 1)
        self.store.change('scene', lambda d: d['items'].append({'id':'a', 'size':192}))
        self.store.edit_character('a', {'size':256})
        self.assertEqual(self.store.read('scene')['items'][0]['size'], 256)
        self.assertEqual(json.loads((Path(self.temp.name)/'scene.json').read_text())['items'][0]['size'], 256)

    def test_corrupt_input_leaves_no_partial_cache(self):
        path = Path(self.temp.name) / 'broken.gif'; path.write_bytes(b'broken')
        with self.assertRaises(Exception): self.store.prepare(path)
        self.assertEqual(list((Path(self.temp.name)/'cache').iterdir()), [])

if __name__ == '__main__': unittest.main()
