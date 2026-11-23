#!/bin/bash
# Build SpikeGLX's offline variant (SpikeGLX_NISIM) natively on Linux, arm64
# (aarch64) or x86-64, with Qt's own Qt 6.10.3 binaries (aqtinstall) and the
# system GCC. No root needed.
#
# usage: linux/compile.sh WORKDIR
#   Puts Qt in WORKDIR/Qt (unless QTDIR names an existing Qt), builds in
#   WORKDIR/build and leaves the program in WORKDIR/out/SpikeGLX_NISIM.
# env:   QTDIR (skip the download), QT_VERSION (default 6.10.3)
set -euo pipefail
SRC=$(cd "$(dirname "$0")/.." && pwd)
W=$(mkdir -p "${1:?usage: linux/compile.sh WORKDIR}" && cd "$1" && pwd)
QT_VERSION=${QT_VERSION:-6.10.3}

case $(uname -m) in
    aarch64) HOST=linux_arm64; ARCH=linux_gcc_arm64; QTSUB=gcc_arm64 ;;
    x86_64)  HOST=linux;       ARCH=linux_gcc_64;    QTSUB=gcc_64 ;;
    *) echo "unsupported machine $(uname -m)" >&2; exit 1 ;;
esac

if [ -z "${QTDIR:-}" ]; then
    QTDIR=$W/Qt/$QT_VERSION/$QTSUB
    if [ ! -x "$QTDIR/bin/qmake" ]; then
        python3 -m venv "$W/aqt-venv"
        "$W/aqt-venv/bin/pip" install --quiet aqtinstall==3.3.0
        # icu: Qt's own libQt6Core needs ICU 73, which most distributions don't ship.
        "$W/aqt-venv/bin/aqt" install-qt "$HOST" desktop "$QT_VERSION" "$ARCH" \
            --archives qtbase qtsvg icu -O "$W/Qt"
    fi
fi
if [ ! -x "$QTDIR/bin/qmake" ]; then
    echo "no Qt in QTDIR=$QTDIR (no bin/qmake there)" >&2
    exit 1
fi
echo "Qt: $QTDIR ($("$QTDIR/bin/qmake" -query QT_VERSION))"
g++ --version | head -1

mkdir -p "$W/build" "$W/out"
cd "$W/build"
# The .pro forces CONFIG += debug and a fixed DESTDIR for unix; override both.
"$QTDIR/bin/qmake" "$SRC/SpikeGLX40.pro" -spec linux-g++ -after \
    "CONFIG-=debug" "CONFIG+=release" "DESTDIR=$W/out"
make -j"$(nproc)"
file "$W/out/SpikeGLX_NISIM"
