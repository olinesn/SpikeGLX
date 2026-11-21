#!/bin/bash
# Pack a built SpikeGLX_NISIM into an AppImage the way upstream packs its x86-64
# Linux build (linuxdeploy + linuxdeploy-plugin-qt), then lay it out like
# upstream's SpikeGLX_pkg folder: the AppImage with _Help beside it.
#
# usage: linux/package_appimage.sh QTDIR SPIKEGLX_NISIM OUTDIR
#   OUTDIR/SpikeGLX_pkg/SpikeGLX-<arch>.AppImage, OUTDIR/SpikeGLX_pkg/_Help/...
# env:   TOOLS (where the linuxdeploy AppImages are kept; default OUTDIR/tools)
set -euo pipefail
SRC=$(cd "$(dirname "$0")/.." && pwd)
QTDIR=$(cd "${1:?usage: package_appimage.sh QTDIR SPIKEGLX_NISIM OUTDIR}" && pwd)
EXE=$(realpath "${2:?}")
OUT=$(mkdir -p "${3:?}" && cd "$3" && pwd)
TOOLS=${TOOLS:-$OUT/tools}
A=$(uname -m)

# linuxdeploy publishes only rolling "continuous" builds; print their hashes so
# a run's log says exactly which ones it used.
mkdir -p "$TOOLS"
for t in linuxdeploy linuxdeploy-plugin-qt; do
    f=$TOOLS/$t-$A.AppImage
    if [ ! -x "$f" ]; then
        curl -fsSL -o "$f" "https://github.com/linuxdeploy/$t/releases/download/continuous/$t-$A.AppImage"
        chmod +x "$f"
    fi
    sha256sum "$f"
done

export APPIMAGE_EXTRACT_AND_RUN=1   # the tools run without FUSE (containers, CI)
export QMAKE=$QTDIR/bin/qmake       # tells the Qt plugin which Qt to bundle
export LD_LIBRARY_PATH=$QTDIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export PATH=$TOOLS:$PATH            # linuxdeploy finds its Qt plugin on PATH
export LDAI_OUTPUT=SpikeGLX-$A.AppImage OUTPUT=SpikeGLX-$A.AppImage

cd "$OUT"
rm -rf AppDir SpikeGLX_pkg "SpikeGLX-$A.AppImage"
"$TOOLS/linuxdeploy-$A.AppImage" --appdir AppDir \
    -e "$EXE" -d "$SRC/linux/spikeglx.desktop" -i "$SRC/linux/spikeglx.png" \
    --plugin qt --output appimage

mkdir SpikeGLX_pkg
mv "SpikeGLX-$A.AppImage" SpikeGLX_pkg/
cp -r "$SRC/_Help" SpikeGLX_pkg/
cp "$SRC/linux/ReadMe.txt" SpikeGLX_pkg/
ls -la SpikeGLX_pkg
