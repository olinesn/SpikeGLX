# SpikeGLX offline build for Linux on Arm (aarch64)

*Written by Claude Code.*

This fork's `dev` branch also builds SpikeGLX's offline variant, `SpikeGLX_NISIM`, natively for
64-bit Arm Linux (aarch64), with Qt 6.10.3. Upstream ships the same variant for x86-64 Linux as
an AppImage (`SpikeGLX_Linux_offline.zip` on the SpikeGLX download page); this is the Arm
counterpart, built and packed the same way. It is unofficial. The scripts are written to work on
x86-64 as well, but were only run on Arm.

**It can't record.** As in upstream's Linux build, the imec, VISA and NI-DAQmx backends are
turned off: imec's NeuropixAPI exists only as a Windows x64 DLL. It opens recordings in the File
Viewer and Shank Viewer, edits IMRO tables, verifies SHA1s and runs the command server.

## Source changes

One line beyond what `dev` already has for macOS: `Src-graphs/SVToolsMR.h` included
`"TspikeEditor.h"`, but the file is `TSpikeEditor.h`. Windows and macOS file systems ignore the
case; Linux doesn't, so the build stopped there. Upstream's own Linux release (v20260901)
predates the line. Nothing else needed changing: upstream keeps its Linux code paths working, and
the parts of SpikeGLX that are built have no x86-only code.

The `.pro` is untouched; `compile.sh` overrides its unix `CONFIG += debug` and `DESTDIR` with
qmake `-after`, as the macOS build does.

## Build it

Needs GCC, make, Python 3 (for aqtinstall) and the OpenGL headers. No root for anything else.
On Ubuntu 24.04:

```bash
sudo apt install build-essential python3-venv libgl-dev    # once
git clone -b dev https://github.com/olinesn/SpikeGLX.git
SpikeGLX/linux/compile.sh work                  # Qt into work/Qt, program in work/out
SpikeGLX/linux/package_appimage.sh work/Qt/6.10.3/gcc_arm64 work/out/SpikeGLX_NISIM work/pkg
```

- `compile.sh` installs Qt's own Qt 6.10.3 build (`linux_gcc_arm64`: `qtbase`, `qtsvg`, `icu`;
  196 MB) with aqtinstall, then runs qmake and make. Set `QTDIR` to use a Qt you already have.
- **Distribution Qt doesn't work:** SpikeGLX needs Qt 6.9 or newer (`QThread::setServiceLevel`,
  `QCheckBox::checkStateChanged`); Ubuntu 24.04 has 6.4.2, and NVIDIA's JetPack ships no Qt 6.
- `package_appimage.sh` packs the program with linuxdeploy and linuxdeploy-plugin-qt (as
  upstream does), and lays out `SpikeGLX_pkg/` like upstream's: `SpikeGLX-aarch64.AppImage`,
  `_Help/` (the help pages are read from there) and `ReadMe.txt`.

Running the bare program also works: start it from a writable folder. Qt's X11 plugin then
needs `libxcb-cursor0` from the system (desktop installs have it; the AppImage brings its own). Without an AppImage,
SpikeGLX uses the **current folder** as its app folder (`_Configs` for settings, `_Help`, …);
from an AppImage it uses the AppImage's folder.

## Requirements to run

- glibc 2.39 or newer (Ubuntu 24.04, Debian 13 or later): Qt's own aarch64 binaries are built on
  Ubuntu 24.04. Ubuntu 22.04 (JetPack 6) and Raspberry Pi OS bookworm are too old.
- An X11 session or XWayland (SpikeGLX forces Qt's `xcb` platform on Linux) and OpenGL with the
  compatibility profile: the graphs and the shank views use fixed-function OpenGL.
- For the AppImage, FUSE 2 (`libfuse2t64`), or run it with `--appimage-extract-and-run`.

## What is tested

On an NVIDIA Jetson AGX Orin (12 Arm cores, Ubuntu 24.04, NVIDIA's driver with OpenGL 4.6):

- **Build:** `compile.sh` from an empty folder, Qt download included, in 1 min 46 s; the compile
  alone takes about 70 s on 12 cores. `package_appimage.sh` in 16 s; the AppImage is 32 MB and
  holds the same libraries and Qt plugins as upstream's x86-64 one. The system's OpenGL library
  is left out, as it must be, and nothing in it points at the build machine.
- **`smoke_test.py`**, on the bare program and on the AppImage: start-up (the command server
  answers within 0.5 s), `GETVERSION`, the data-folder commands (`SETDATADIR`,
  `SETMULTIDRIVEENABLE`), `VERIFYSHA1` passing a synthetic recording and failing a copy with one
  byte changed, and settings saved in `_Configs` (beside the AppImage for the AppImage).
- **On the desktop:** the console; the File Viewer on a synthetic NP1.0 recording
  (`macos/make_synth_np1.py`) draws its traces with the spikes visible; its Shank Viewer draws
  the probe on the Edit tab. So the fixed-function OpenGL works with NVIDIA's driver. These
  windows were opened by a test-only hook calling the same code as the menus (the desktop was
  locked), not by clicking.
- **Not tested:** clicking the real menus and the file dialog; Wayland without XWayland; Mesa
  drivers (AMD, Intel, Raspberry Pi); any other Arm board; x86-64 with these scripts; File
  Viewer features past the first screen; LF, NI and OneBox files; PAR2; the gate/trigger server.

## Known issues

- No audio output (the audio code is Windows-only); logged at start-up.
- Thread IDs in the console log are long numbers (Linux `pthread_t` values).
- **No Simulated Probes.** They are part of the imec backend, which this build leaves out with
  the rest of it. A test build that compiled the imec backend against a stand-in for imec's
  library (one that reports no hardware) did replay 1 to 4 simulated NP2.0 probes at the full
  rate on the Jetson, using about 0.11 of a core per probe; that stand-in is not part of this
  fork.
- The command server's `QUIT`/`EXIT`/`BYE` only close the connection, as on Windows; the app keeps
  running.
