"""
sigprocmask.py - Prevents Go runtime from ever blocking SIGILL (Signal 4).

ROOT CAUSE of intermittent Exit Code 132 (SIGILL) on ARMv8.0 CPUs:
When Go creates OS threads (runtime.newosproc), it executes:
    sigfillset(&set) // sets all 64 bits including SIGILL
    sigprocmask(_SIG_SETMASK, &set, &old)
Per POSIX and Linux kernel specification, if a hardware fault (SIGILL) occurs while
the signal is masked in the thread's signal mask, the kernel KILLS THE PROCESS
IMMEDIATELY, bypassing all signal handlers (even LD_PRELOAD handlers).

On ARMv8.0 CPUs, every atomic operation is an LSE instruction that triggers a SIGILL trap.
If an atomic instruction runs on ANY thread while SIGILL is blocked, the kernel kills
the process instantly with exit code 132 (128 + 4 = 132).

This patch intercepts runtime.sigprocmask and dynamically CLEARS bit 3 (SIGILL)
from the incoming sigset mask before invoking the rt_sigprocmask syscall (135).
This guarantees that SIGILL is NEVER blocked on any thread, allowing liblse_compat.so
to ALWAYS catch and emulate LSE atomic instructions seamlessly.
"""
import sys
import os
from typing import Tuple, Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PATCHES_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, os.path.join(PATCHES_ROOT, "engine"))

import byte_replacer

# Target: original runtime.sigprocmask implementation in sys_linux_arm64.s (40 bytes)
# ldrsw x0, [sp, #8]
# ldr x1, [sp, #16]
# ldr x2, [sp, #24]
# ldrsw x3, [sp, #32]
# mov x8, #135
# svc #0
# cmn x0, #0xfff
# b.lo +0xc
# mov x0, xzr
# str x0, [x0]
TARGET = bytes.fromhex("e00b80b9e10b40f9e20f40f9e32380b9e81080d2010000d41ffc3fb163000054e0031faa000000f9")

# Replacement: loads arguments, clears bit 3 (SIGILL) if set != NULL, invokes syscall (40 bytes)
# ldp x0, x1, [sp, #8]
# ldp x2, x3, [sp, #24]
# cbz x1, +16
# ldr x8, [x1]
# and x8, x8, #0xfffffffffffffff7 (clear bit 3 = SIGILL)
# str x8, [x1]
# mov x8, #135
# svc #0
# nop
# ret
REPLACEMENT = bytes.fromhex("e08740a9e28f41a9810000b4280040f908f97c92280000f9e81080d2010000d41f2003d5c0035fd6")

MIN_EXPECTED_COUNT = 1

def apply(data: bytearray, verify: bool = False, dry_run: bool = False, allow_missing: bool = False) -> Tuple[bool, Dict[str, Any]]:
    raw_offsets = byte_replacer.find_offsets(data, TARGET)
    pat_offsets = byte_replacer.find_offsets(data, REPLACEMENT)
    
    total = len(raw_offsets) + len(pat_offsets)
    info = {
        "name": "sigprocmask_unblock_sigill",
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
