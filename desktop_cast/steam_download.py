#!/usr/bin/env python3
"""Use the user's installed Steam runtime to download one Workshop item."""
import ctypes as c
import json
import os
import sys
import time
from pathlib import Path
from .workshop import details
from .store import SUPPORTED


def emit(**values):
    print('DESKTOP_CAST ' + json.dumps(values), flush=True)


def download(identity):
    details(identity)  # Validate app ownership of the item before asking Steam to download.
    runtime = Path.home() / '.local/share/Steam/steamrt64/libsteam_api.so'
    if not runtime.exists():
        raise RuntimeError('Steam’s 64-bit runtime was not found. Install and open Steam first.')
    os.environ['SteamAppId'] = '3474900'; os.environ['SteamGameId'] = '3474900'
    api = c.CDLL(str(runtime))
    api.SteamAPI_InitSafe.restype = c.c_bool
    if not api.SteamAPI_InitSafe():
        raise RuntimeError('Open Steam and sign in to the account that owns animaEngine, then try again.')
    try:
        api.SteamAPI_SteamUGC_v021.restype = c.c_void_p
        ugc = api.SteamAPI_SteamUGC_v021()
        if not ugc: raise RuntimeError('Steam’s Workshop interface is unavailable.')
        api.SteamAPI_ISteamUGC_DownloadItem.argtypes = [c.c_void_p, c.c_uint64, c.c_bool]
        api.SteamAPI_ISteamUGC_DownloadItem.restype = c.c_bool
        api.SteamAPI_ISteamUGC_GetItemState.argtypes = [c.c_void_p, c.c_uint64]
        api.SteamAPI_ISteamUGC_GetItemState.restype = c.c_uint32
        api.SteamAPI_ISteamUGC_GetItemDownloadInfo.argtypes = [c.c_void_p, c.c_uint64, c.POINTER(c.c_uint64), c.POINTER(c.c_uint64)]
        api.SteamAPI_ISteamUGC_GetItemDownloadInfo.restype = c.c_bool
        api.SteamAPI_ISteamUGC_GetItemInstallInfo.argtypes = [c.c_void_p, c.c_uint64, c.POINTER(c.c_uint64), c.c_char_p, c.c_uint32, c.POINTER(c.c_uint32)]
        api.SteamAPI_ISteamUGC_GetItemInstallInfo.restype = c.c_bool
        number = int(identity)
        if not api.SteamAPI_ISteamUGC_DownloadItem(ugc, number, True):
            raise RuntimeError('Steam declined this download. Check that animaEngine is installed and owned by the signed-in account.')
        started = time.monotonic()
        while time.monotonic() - started < 600:
            api.SteamAPI_RunCallbacks()
            state = api.SteamAPI_ISteamUGC_GetItemState(ugc, number)
            received, total = c.c_uint64(), c.c_uint64()
            api.SteamAPI_ISteamUGC_GetItemDownloadInfo(ugc, number, c.byref(received), c.byref(total))
            emit(progress=received.value, total=total.value)
            if state & 4 and not state & (8 | 16 | 32):
                size, updated, folder = c.c_uint64(), c.c_uint32(), c.create_string_buffer(4096)
                if api.SteamAPI_ISteamUGC_GetItemInstallInfo(ugc, number, c.byref(size), folder, len(folder), c.byref(updated)):
                    root = Path(os.fsdecode(folder.value))
                    paths = [str(p) for p in root.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED]
                    if not paths: raise RuntimeError('Downloaded, but this item contains no supported images. Video and scripted items are not supported yet.')
                    emit(files=paths); return
            time.sleep(.3)
        raise RuntimeError('Steam download timed out. Check Steam’s Downloads page, then try again.')
    finally:
        api.SteamAPI_Shutdown()

if __name__ == '__main__':
    try: download(sys.argv[1])
    except Exception as error:
        emit(error=str(error)); raise SystemExit(1)
