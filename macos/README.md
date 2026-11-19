# SpikeGLX offline build for Apple Silicon Macs

*Written by Claude Code.*

This branch (`macos-arm64-offline`) builds SpikeGLX's offline variant, `SpikeGLX_NISIM.app`, as a
native arm64 macOS app with Qt 6.10.3. It is based on `billkarsh/SpikeGLX` master at `cbcd078`.
SpikeGLX doesn't officially support macOS; this is an unofficial build for looking at data.

**It can't acquire.** The imec, VISA and NI-DAQmx backends are turned off, and none of their
libraries exist for macOS. It can open recordings in the File Viewer, show and edit IMRO tables
(Shank Viewer, IMRO Table Editor), verify SHA1s and run the command server.

## Download

Open the Actions tab, then the latest "macOS arm64 offline build" run. Download the artifact
`SpikeGLX_NISIM-macos-arm64`. It holds `SpikeGLX_NISIM-macos-arm64.zip`; unzip that too.

- The app is ad-hoc signed, not notarized. macOS blocks it after a download until you clear the
  quarantine flag: `xattr -dr com.apple.quarantine SpikeGLX_NISIM.app` (or right-click ▸ Open).
- Keep the app in a folder you can write to. Settings go in a `_Configs` folder beside the `.app`,
  as they go beside the program on Windows.
- On first start SpikeGLX creates `~/SGL_DATA` as its data folder and says so in a dialog.

## Changes to the source

Three commits on top of upstream (25 lines added, 12 removed, in 4 files):

1. **`Src-remote/CmdServer.cpp`**: the remote commands `SETDATADIR` and `SETMULTIDRIVEENABLE`
   called `MainApp` directly on the command server's worker thread. Both rebuild the Data Directory
   menu, and macOS aborts an app whose main menu changes off the main thread. They now run on the
   GUI thread (`QMetaObject::invokeMethod`, `Qt::BlockingQueuedConnection`), like every other
   command. Windows doesn't abort, but Qt widgets aren't thread-safe there either, so this is an
   upstream bug too.
2. **`Src-main/Util_osdep.cpp`, `Src-main/Util.cpp`**: `<OpenGL/gl.h>` instead of `<GL/gl.h>`;
   `QElapsedTimer` instead of `QTime::start/elapsed` (removed in Qt 6); `appPath()` uses the folder
   holding the `.app` (Finder starts apps in `/`, so settings never saved).
3. **`SpikeGLX40.pro`**: `HAVE_IMEC`, `HAVE_VISA`, `HAVE_NIDAQmx` commented out (upstream's own
   switch for the simulated build).

The rest is new: `.github/workflows/macos-arm64-offline.yml` and this folder.

## Build it yourself

Needs Xcode or its Command Line Tools, and Python 3 for aqtinstall. No admin rights.

```bash
python3 -m venv aqt && aqt/bin/pip install aqtinstall==3.3.0
aqt/bin/aqt install-qt mac desktop 6.10.3 clang_64 --archives qtbase qtsvg -O Qt
mkdir build out && cd build
../Qt/6.10.3/macos/bin/qmake ../SpikeGLX/SpikeGLX40.pro -spec macx-clang -after \
    "CONFIG-=debug" "CONFIG+=release" "CONFIG+=sdk_no_version_check" \
    "DESTDIR=$PWD/../out" "QMAKE_APPLE_DEVICE_ARCHS=arm64" \
    "DEFINES+=GL_SILENCE_DEPRECATION" "QMAKE_CXXFLAGS+=-include arm_acle.h"
make -j"$(sysctl -n hw.ncpu)"
cd .. && zsh SpikeGLX/macos/package_mac.sh Qt/6.10.3/macos/bin out/SpikeGLX_NISIM.app
```

Why the qmake overrides: the `.pro` forces `CONFIG += debug` and a Linux `DESTDIR` on unix, and
Qt 6.10.3's `qyieldcpu.h` calls `__yield()` without declaring it, which clang 21 rejects
(`-include arm_acle.h` fixes that). `package_mac.sh` runs `macdeployqt`, thins every binary to
arm64 (57 → 29 MB), removes rpaths that point outside the bundle and signs it ad hoc.

## What is tested

- **Every CI run:** build, package, `check_bundle.sh` (every binary arm64-only, nothing linked
  from outside the bundle except macOS itself, signature valid) and `smoke_test.py` (starts from
  `/`, sends `GETVERSION`, `GETDATADIR`, `SETDATADIR` and `SETMULTIDRIVEENABLE` over
  127.0.0.1, checks the app stays up and saves its settings beside the `.app`).
- **By hand on an Apple Silicon Mac:** the File Viewer on a synthetic NP1.0 recording
  (`make_synth_np1.py`) draws traces; the Shank Viewer's IMRO edit tab and the IMRO Table Editor
  (NP2.0 4-shank) draw the probes; Verify SHA1 passes a good file and fails a corrupted one.
- **Not tested:** clicking the real menus and the native file dialog; File Viewer features past
  the first screen; LF, NI and OneBox files; the Configure dialog and simulated runs; Wave Planner;
  PAR2 (its helper tool ships for Windows only); the gate/trigger server.

## Known issues

- No audio output (the audio code is Windows-only).
- Qt uses a legacy OpenGL context, so the fixed-function drawing works, but Apple's OpenGL layer
  draws stippled lines and polygon modes on the CPU. Slower, not wrong.
- In dark mode, read-only fields such as "Part number" are hard to read.
