"""
sigill_handler.py - Preserves LD_PRELOAD SIGILL handler for liblse_compat.so by skipping Go rt_sigaction for SIGILL (4).

v2: Dynamic call-site scanning — patches ALL matching rt_sigaction call sites
instead of hardcoding an expected count of 2. Newer Go versions may have
additional call sites that were previously missed, causing the SIGILL handler
to be silently replaced at runtime (race condition → exit code 132).
"""
import sys
import os
from typing import Tuple, Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PATCHES_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, os.path.join(PATCHES_ROOT, "engine"))

import byte_replacer

TARGET = bytes.fromhex("e00740f9e10b40f9e20f40f9e31340f9c81080d2010000d4e02b00b9c0035fd6")
REPLACEMENT = bytes.fromhex("e08740a9e28f41a91f1000f1c81080d240000054010000d4ff2b00b9c0035fd6")

# Minimum expected call sites. We now allow MORE than this count (newer Go versions).
# Fail only if zero sites are found (signature mismatch with this Go binary).
MIN_EXPECTED_COUNT = 2

def apply(data: bytearray, verify: bool = False, dry_run: bool = False, allow_missing: bool = False) -> Tuple[bool, Dict[str, Any]]:
    raw_offsets = byte_replacer.find_offsets(data, TARGET)
    pat_offsets = byte_replacer.find_offsets(data, REPLACEMENT)
    
    total = len(raw_offsets) + len(pat_offsets)
    info = {
        "name": "sigill",
        "min_expected": MIN_EXPECTED_COUNT,
        "total_found": total,
        "raw_count": len(raw_offsets),
        "patched_count": len(pat_offsets),
        "raw_offsets": [hex(x) for x in raw_offsets],
        "patched_offsets": [hex(x) for x in pat_offsets]
    }

    if total == 0:
        if allow_missing:
            info["status"] = "skipped_missing"
            return True, info
        info["status"] = "missing_signature"
        return False, info

    # Accept any count >= 1 (don't fail on unexpected extra call sites)
    if total < MIN_EXPECTED_COUNT:
        info["status"] = f"suspicious_low_count_{total}"
        # Still proceed — patch what we can find, but flag it
    
    if verify:
        ok = (len(raw_offsets) == 0 and len(pat_offsets) >= MIN_EXPECTED_COUNT)
        info["status"] = "verified" if ok else "unverified"
        return ok, info

    if len(raw_offsets) == 0:
        info["status"] = "already_patched"
        return True, info

    if not dry_run:
        for off in raw_offsets:
            data[off:off + len(REPLACEMENT)] = REPLACEMENT
        info["status"] = f"patched_{len(raw_offsets)}_sites"
    else:
        info["status"] = f"dry_run_{len(raw_offsets)}_sites"

    return True, info
