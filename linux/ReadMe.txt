SpikeGLX offline build for Linux (unofficial, from the olinesn/SpikeGLX fork).

It opens recordings in the File Viewer and Shank Viewer, edits IMRO tables,
verifies SHA1s and runs the command server. It can't record: there is no imec,
NI or OneBox support in it.

- Keep the AppImage and _Help together in this folder. SpikeGLX writes its
  settings (_Configs) beside the AppImage, so the folder must be writable.
- You may have to run: chmod +x SpikeGLX-*.AppImage
- AppImages need FUSE 2 (Ubuntu: libfuse2t64). Without it, run the AppImage
  with --appimage-extract-and-run.
- Needs glibc 2.39 or newer (Ubuntu 24.04, Debian 13 and later).
