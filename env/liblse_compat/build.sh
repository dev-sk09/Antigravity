#!/usr/bin/env bash
# build.sh - compile liblse_compat.so targeting baseline ARMv8.0-A
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
CC="${CC:-clang}"
GLIBC_DIR="$ROOT/modules/core/glibc"
CFLAGS="${CFLAGS:--march=armv8-a -mno-outline-atomics -O2 -Wall -fPIC -shared -nostdlib}"

"$CC" $CFLAGS "$GLIBC_DIR/libc.so.6" "$GLIBC_DIR/libdl.so.2" "$DIR/liblse_compat.c" -o "$DIR/liblse_compat.so"
echo "Built: $DIR/liblse_compat.so"

cp "$DIR/liblse_compat.so" "$ROOT/app/src/main/assets/runtime/lib/liblse_compat.so"
echo "Staged: $ROOT/app/src/main/assets/runtime/lib/liblse_compat.so"

SHA="$(sha256sum "$DIR/liblse_compat.so" | awk '{print $1}')"
MANIFEST="$ROOT/app/src/main/assets/runtime/manifest.json"
sed -i -E "s/\"lib\/liblse_compat\.so\": \"[a-f0-9]+\"/\"lib\/liblse_compat.so\": \"$SHA\"/" "$MANIFEST"
echo "Updated manifest with sha256: $SHA"

