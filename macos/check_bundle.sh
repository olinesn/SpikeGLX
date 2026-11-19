#!/bin/bash
# Usage: check_bundle.sh <path/to/App.app>
# Fails if any Mach-O in the bundle is not arm64-only, links anything outside
# the bundle other than /System/Library and /usr/lib, or the signature is invalid.
APP=$1
bad=0
n=0
while IFS= read -r -d '' f; do
    file "$f" | grep -q 'Mach-O' || continue
    n=$((n + 1))
    archs=$(lipo -archs "$f")
    if [ "$archs" != arm64 ]; then
        echo "not arm64-only: $f ($archs)"; bad=1
    fi
    outside=$(otool -L "$f" | tail -n +2 | awk '{print $1}' |
        grep -v -E '^(@rpath/|@executable_path/|@loader_path/|/System/Library/|/usr/lib/)')
    if [ -n "$outside" ]; then
        echo "outside reference in $f: $outside"; bad=1
    fi
done < <(find "$APP" -type f -print0)
codesign --verify --deep --strict "$APP" || bad=1
echo "$n Mach-O files checked"
[ $bad = 0 ] && echo "bundle OK"
exit $bad
