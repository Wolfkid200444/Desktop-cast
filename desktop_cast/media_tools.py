"""Local creator utilities. Sources are always preserved."""
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from PIL import Image, ImageChops
from .store import DATA


def export_asset(asset, target, color=None, tolerance=0):
    if asset['frames'] > 600:
        raise ValueError('Export is limited to 600 frames. Choose a shorter animation.')
    target = Path(target)
    source = Path(asset['source']).resolve()
    if target.resolve() == source:
        raise ValueError('Choose a new filename so the source stays intact.')
    target.parent.mkdir(parents=True, exist_ok=True)
    def frames():
        for index in range(asset['frames']):
            with Image.open(Path(asset['directory']) / f'{index:05d}.png') as image:
                frame = image.convert('RGBA')
            if color:
                rgb = frame.convert('RGB')
                diff = ImageChops.difference(rgb, Image.new('RGB',frame.size,tuple(color)))
                red, green, blue = diff.split()
                distance = ImageChops.lighter(ImageChops.lighter(red,green),blue)
                keep = distance.point(lambda value: 0 if value <= tolerance else 255)
                frame.putalpha(ImageChops.multiply(frame.getchannel('A'),keep))
            yield frame
    sequence = frames(); first = next(sequence)
    temporary = target.with_name('.' + target.stem + '-' + uuid.uuid4().hex + '.apng')
    try:
        first.save(temporary, format='PNG', save_all=asset['frames']>1, append_images=list(sequence),
                   duration=asset['durations'], loop=0, disposal=0, blend=0)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return [str(target)]


def convert_video(source, seconds):
    if not shutil.which('ffmpeg'): raise ValueError('Install ffmpeg to convert video files.')
    directory = DATA / 'exports'; directory.mkdir(parents=True, exist_ok=True)
    output = directory / f'{Path(source).stem}-{uuid.uuid4().hex[:6]}.apng'
    with tempfile.TemporaryDirectory(prefix='video-',dir=DATA) as temporary:
        pattern = str(Path(temporary) / '%05d.png')
        command=['ffmpeg','-nostdin','-v','error','-i',str(source),'-t',str(seconds),'-an',
                 '-vf',"fps=10,scale=320:320:force_original_aspect_ratio=decrease",'-frames:v','600',pattern]
        process=subprocess.run(command, capture_output=True,text=True,timeout=180)
        if process.returncode: raise ValueError(process.stderr[-1200:] or 'ffmpeg could not decode the video.')
        paths=sorted(Path(temporary).glob('*.png'))
        if not paths: raise ValueError('The video produced no frames.')
        def frames():
            for path in paths:
                with Image.open(path) as image: yield image.convert('RGBA')
        sequence=frames(); first=next(sequence)
        first.save(output,format='PNG',save_all=True,append_images=list(sequence),duration=100,loop=0)
    return [str(output)]
