# Desktop Cast

Native KDE Wayland desktop animation player with a local library, animaEngine Workshop browser, creator tools, and per-character controls. It uses PySide6, Pillow, and Quickshell. It never launches animaEngine or Proton.

## Open

Find **Desktop Cast** in the application menu, or run:

```sh
./run.sh
```

## Library

Use **Add animation** for GIF, APNG, animated WebP, PNG, JPEG, or BMP. Select a thumbnail to preview it. Choose width, playback FPS, screen, and default layer, then **Launch animation**. Double-clicking a thumbnail also launches it. New animations default to 15 FPS. FPS 0 / Original preserves source timing.

Ctrl-select multiple thumbnails and use **Remove selected** to remove their library entries. Source files and running characters stay intact. **Open file location** opens the original file's folder.

Select an entry under **Running characters** for its Controls panel, audio attachment, or removal. Closing the window keeps overlays running in the system tray. Use the tray menu or Settings to quit.

## Right-click controls

Right-click a desktop character to open the native control panel:

- Keep above other windows, or place on the desktop layer below normal windows.
- Lock position, click-through, hide under cursor, and pause.
- Change width, FPS, rotation, and horizontal / vertical flip while running.
- Reset controls, close the panel, or close that character.

Drag an unlocked character to move it across monitors or partly beyond a screen edge. Characters spanning adjacent monitors render on both. Choose a monitor in Library and use **Center on screen** to move or recover the selected running character. Scroll over a character to resize it. Input passes through outside character bounding rectangles; transparent pixels inside those rectangles normally receive input.

**Click-through** removes the whole character from the input region, without an on-character button. With the optional KDE helper installed, **hold Ctrl and right-click the character** to reopen its menu. Holding Ctrl temporarily restores character input; releasing it restores click-through. The compact control panel is 320 pixels wide with a separate **Edit live animation** page for size, FPS and rotation. Click outside the panel to dismiss it.

The shortcut uses a small user-local KWin helper, loaded while Desktop Cast runs. It exposes only Ctrl held/released state over the session bus. It does not capture typed text, log keys, or transmit anything. Other compositors, or installations without the matching helper, can use **Running characters → Controls…** or **Ctrl+E while Desktop Cast is focused**.

**Ctrl+Shift+R while Desktop Cast is focused**, or **Settings → Recover character controls**, resets locks, click-through, hover hiding, pause, speed, size, rotation, flips, and audio. Existing placement and library files are kept.

**Attach audio** pairs a local MP3, WAV, OGG, FLAC, or M4A with the selected running character. Audio loops independently of the image loop and pauses with the character or when overlays are hidden. Codec availability depends on the installed Qt Multimedia backend.

## Workshop

The **Workshop** tab browses animaEngine's public Steam Workshop with thumbnails, keyword search, popular / top-rated / newest sorting, and pagination. Search also accepts a Steam Workshop URL or numeric item ID.

Select an item and click **Download and add to library**. The installed Steam client downloads it, progress appears in Desktop Cast, and supported images are prepared in the background and added to the library. Steam must be running and signed into an account that owns animaEngine. No API key is required, and downloading does not subscribe to the item.

**Open item in Steam** opens the original listing. **Tools → Sync downloaded Workshop items** imports files already downloaded in your Steam libraries. Private/unavailable items and items belonging to other apps are rejected. Video-only or scripted Workshop items cannot play directly.

Browsing uses Steam's public page data, which can change. Downloads use the Steamworks library in this computer's existing Steam runtime; it is not bundled with Desktop Cast. Quitting Desktop Cast stops its download helper, but a transfer already queued in Steam may continue in Steam.

## Tools

- **Remove background by color** removes a chosen solid color, with a tolerance control, from the selected animation. It exports a new APNG and imports it. It is a color key, not AI segmentation.
- **Convert video to animation** converts the first 1–60 seconds of a local video to APNG at 10 FPS, up to 320 pixels, then imports it. Audio is omitted. Requires ffmpeg.
- **Export GIF / WebP as APNG** exports the selected prepared animation, preserving alpha and timing.

Export/color-key operations are limited to 600 frames. Tools preserve source files. AI background removal, Workshop publishing, app-triggered profiles, automatic walking, and window-edge physics are not included.

## Data, dependencies, and verification

Library, cached frames, scene settings, thumbnails, exports, and overlay logs live in `$XDG_DATA_HOME/desktop-cast`, defaulting to `~/.local/share/desktop-cast`. Existing source checkouts with a `.state/` directory keep using it. `DESKTOP_CAST_DATA` can select a different directory. `run.sh` clears conflicting Python environment variables for this process only.

Images are prepared in background workers as composited RGBA PNG frames with source timing. Prepared frames fit within 512×512 pixels, retain their aspect ratio, and default to 192 pixels wide. Width is adjustable from 64 to 640 pixels. Source limits: 40 megapixels and 1,800 frames. Animations loop continuously unless paused or hidden.

Source dependencies: Python 3.10+, PySide6, Pillow, Quickshell, and KDE Plasma Wayland. Install Quickshell through your distribution and Python dependencies with `pip install -r requirements.txt` in a virtual environment. FFmpeg is optional for video conversion. The Ctrl helper additionally requires matching KWin development headers.

```sh
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -v
```

Tests cover alpha/timing, cache/import behavior, atomic scene changes, Workshop validation, controls, APNG export, screen-size initialization, and close-to-tray behavior.


## KWin Ctrl helper

The helper source is in `integrations/kwin-modifiers/`. The installed effect is `~/.local/share/kwin/effects/desktopcast-modifiers`. It is not enabled automatically at login; Desktop Cast loads it and unloads the instance it owns on exit. No KWin restart or system package changes are needed for the initial install.

The native helper is tied to the installed KWin version. Desktop Cast checks the installed and running KWin versions against the helper build version before loading it. After a KWin update, rebuild with the matching development headers and restart the desktop session if the running KWin is older than the installed headers:

```sh
./integrations/kwin-modifiers/install.sh
```

Build dependencies are CMake, a C++ compiler, Qt6 development files, and KWin development headers. If the helper is unavailable, app-side Controls and Ctrl+E remain available.

## Background operation

Closing the main window leaves Desktop Cast running in the system tray and keeps
your characters on the desktop. Click its tray icon or open Desktop Cast again to
show the existing window. The tray menu includes Show / hide characters and Quit
Desktop Cast. Settings also includes a Quit action. On desktops without a system
tray, closing exits cleanly instead of leaving an inaccessible process.

## Versions and packages

Current version: 0.2.0. The version lives in VERSION and can be queried with
`python3 app.py --version`. GitHub Actions tests changes and builds AppImage,
Debian, RPM and portable Linux archives. Tags such as v0.1.0 publish a release.
See [packaging notes](docs/packaging.md) for dependencies and compatibility.


## Project layout

- `desktop_cast/`: Python application, library storage, Workshop and media tools.
- `overlays/`: Wayland character rendering, controls and monitor geometry.
- `assets/`: theme and application icon.
- `integrations/kwin-modifiers/`: optional host KWin modifier helper.
- `tests/`: regression tests.
- `packaging/`: Linux package builder and desktop entry.
- `.github/workflows/`: tests, package builds and tagged releases.
- `docs/`: packaging notes. Local preview images are excluded from Git.
