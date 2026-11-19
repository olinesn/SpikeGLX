#!/bin/zsh
# Usage: package_mac.sh <Qt bin dir> <path/to/App.app>
# Bundle Qt (macdeployqt), thin every Mach-O to arm64, ad-hoc sign, verify.
set -e
QTBIN=$1; APP=$2
"$QTBIN/macdeployqt" "$APP" -verbose=1
find "$APP" -type f | while read -r f; do
  if file "$f" | grep -q "universal binary"; then
    lipo "$f" -thin arm64 -output "$f.thin" && mv "$f.thin" "$f"
  fi
done
# drop any rpath that points outside the bundle
EXE="$APP/Contents/MacOS/$(basename "$APP" .app)"
otool -l "$EXE" | awk '/LC_RPATH/{getline; getline; print $2}' | grep -v '^@' | while read -r rp; do
  install_name_tool -delete_rpath "$rp" "$EXE"
done
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
echo "packaged: $APP"
