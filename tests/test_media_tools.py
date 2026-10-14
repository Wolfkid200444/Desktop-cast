import tempfile
import unittest
from pathlib import Path
from PIL import Image
from desktop_cast.media_tools import export_asset
class MediaTests(unittest.TestCase):
    def test_export_removes_color_preserves_other_alpha_and_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for i in range(2):
                frame=Image.new('RGBA',(12,12),(255,255,255,255));frame.putpixel((5,5),(120+i,10,20,128));frame.save(root/f'{i:05d}.png')
            asset={'source':str(root/'original.gif'),'directory':str(root),'frames':2,'durations':[60,140]}
            output=root/'keyed.apng';export_asset(asset,output,(255,255,255),0)
            with Image.open(output) as image:
                self.assertEqual(image.n_frames,2)
                self.assertEqual(image.info['duration'],60)
                self.assertEqual(image.getpixel((0,0))[3],0)
                self.assertEqual(image.getpixel((5,5))[3],128)
                image.seek(1);self.assertEqual(image.info['duration'],140)
            with self.assertRaisesRegex(ValueError,'source'):export_asset(asset,root/'original.gif')
if __name__=='__main__':unittest.main()
