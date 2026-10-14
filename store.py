"""Portable library, animation preparation, and atomic scene storage."""
import fcntl
import hashlib
import json
import os
import shutil
import tempfile
import sys
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
# Existing source checkouts keep their data. Installed builds use a writable XDG directory.
_default_data = ROOT / '.state' if (ROOT / '.state').exists() else Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'desktop-cast'
DATA = Path(os.environ.get('DESKTOP_CAST_DATA', _default_data))
SUPPORTED = {'.gif', '.apng', '.png', '.webp', '.jpg', '.jpeg', '.bmp'}


def initialize():
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'cache').mkdir(exist_ok=True)
    if not (DATA / 'window-request.json').exists():
        change('window-request', lambda d: d.update(nonce=0))
    if not (DATA / 'scene.json').exists():
        change('scene', lambda d: None)
    if not (DATA / 'modifiers.json').exists():
        change('modifiers', lambda d: d.update(held=False, available=False))
    if not (DATA / 'control-request.json').exists():
        change('control-request', lambda d: d.update(nonce=0, id=''))


def read(name):
    try:
        return json.loads((DATA / f'{name}.json').read_text())
    except FileNotFoundError:
        return {'items': [], 'visible': True}


def change(name, mutate):
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / f'{name}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        doc = read(name)
        mutate(doc)
        fd, temporary = tempfile.mkstemp(prefix=f'.{name}-', dir=DATA)
        try:
            with os.fdopen(fd, 'w') as output:
                json.dump(doc, output)
            os.replace(temporary, DATA / f'{name}.json')
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return doc


def prepare(source):
    """Decode composited RGBA frames once, retaining alpha and frame timing."""
    source = Path(source).resolve()
    stat = source.stat()
    key = hashlib.sha256(f'{source}:{stat.st_size}:{stat.st_mtime_ns}:v1'.encode()).hexdigest()[:24]
    destination = DATA / 'cache' / key
    manifest = destination / 'asset.json'
    if manifest.exists():
        return json.loads(manifest.read_text())
    staging = Path(tempfile.mkdtemp(prefix='.import-', dir=DATA / 'cache'))
    try:
        with Image.open(source) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError('Image exceeds the 40 megapixel limit.')
            count = getattr(image, 'n_frames', 1)
            if count > 1800:
                raise ValueError('Animation exceeds 1,800 frames. Trim it before importing.')
            first = 1 if image.info.get('default_image', False) and count > 1 else 0
            durations = []
            size = None
            for index in range(first, count):
                image.seek(index)
                frame = ImageOps.exif_transpose(image.convert('RGBA'))
                frame.thumbnail((512, 512), Image.Resampling.LANCZOS)
                if size is None:
                    size = frame.size
                frame.save(staging / f'{index-first:05d}.png')
                durations.append(max(10, min(60000, int(image.info.get('duration', 100) or 100))))
        asset = {'id': key, 'name': source.stem, 'source': str(source),
                 'directory': str(destination), 'width': size[0], 'height': size[1],
                 'durations': durations, 'frames': len(durations)}
        (staging / 'asset.json').write_text(json.dumps(asset))
        staging.rename(destination)
        return asset
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def add_assets(assets):
    def update(doc):
        existing = {item['id'] for item in doc['items']}
        doc['items'].extend(a for a in assets if a['id'] not in existing)
    return change('library', update)


def edit_character(identity, values):
    def update(doc):
        for item in doc['items']:
            if item['id'] == identity:
                item.update(values)
    return change('scene', update)

CONTROL_DEFAULTS = {'size': 192, 'fps': 15, 'rotation': 0, 'flip_x': False,
                    'flip_y': False, 'locked': False, 'clickthrough': False,
                    'hide_cursor': False, 'paused': False, 'layer': 'overlay',
                    'audio': '', 'volume': 0.7}


def control_values(values):
    """Validate persisted live controls shared by the picker and overlay."""
    result = {}
    for key, value in values.items():
        if key in ('locked', 'clickthrough', 'hide_cursor', 'paused', 'flip_x', 'flip_y'):
            if not isinstance(value, bool): raise ValueError(f'{key} must be a boolean')
            result[key] = value
        elif key in ('size', 'fps', 'rotation'):
            low, high = {'size': (64, 640), 'fps': (0, 120), 'rotation': (-180, 180)}[key]
            result[key] = max(low, min(high, int(value)))
        elif key == 'volume': result[key] = max(0, min(1, float(value)))
        elif key == 'layer':
            if value not in ('overlay', 'desktop'): raise ValueError('Invalid desktop layer')
            result[key] = value
        elif key == 'audio':
            path = Path(value) if value else None
            if path and (not path.is_file() or path.suffix.lower() not in ('.mp3', '.wav', '.ogg', '.flac', '.m4a')):
                raise ValueError('Choose a supported audio file')
            result[key] = str(path.resolve()) if path else ''
    return result
