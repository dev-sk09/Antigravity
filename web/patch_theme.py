#!/usr/bin/env python3
"""
web/patch_theme.py - DeltaMod UI step 1: dark/blue theme.

Rewrites the built-in theme seeds in a staged copy of main.js so the whole UI
(background, cards, sidebar, muted text, borders) is derived from the DeltaMod
palette. The app's own theme picker keeps working: "Default Dark/Light" become
the DeltaMod colors and "Classic Dark/Light" keep the old look.
Idempotent; exits non-zero if an anchor is missing.
"""

import re
import sys

MARK = "/*deltamod-theme*/"

DARK = {"background": "#0a0f1d", "foreground": "#e7edff", "primary": "#4f8cff"}
LIGHT = {"background": "#f3f6fc", "foreground": "#0f1830", "primary": "#2f6ff0"}
DARK_STATUS = {"error": "#f87171", "warning": "#fbbf24", "link": "#6ea2ff", "success": "#34d399"}
LIGHT_STATUS = {"error": "#d64545", "warning": "#b7791f", "link": "#2f6ff0", "success": "#0f9f6e"}


def seed(c):
    return '{background:"%s",foreground:"%s",primary:"%s"}' % (c["background"], c["foreground"], c["primary"])


def preset(c):
    return '{background:"%s",foregroundOverride:"%s",primary:"%s"}' % (c["background"], c["foreground"], c["primary"])


def sub_once(pattern, repl, text, what):
    new, n = re.subn(pattern, repl, text, count=1)
    if n != 1:
        print(f"[theme-patch] anchor not found: {what}", file=sys.stderr)
        sys.exit(1)
    return new


def main(path):
    with open(path, "r", encoding="utf-8") as f:
        s = f.read()
    if MARK in s:
        print("[theme-patch] already applied")
        return

    # 1. Default seeds used when the user has not picked a custom theme.
    s = sub_once(
        r'(var [\w$]+=)\{background:"#F9F9F9",foreground:"#101010",primary:"#007acc"\}'
        r',([\w$]+=)\{background:"#101010",foreground:"#cccccc",primary:"#007acc"\}',
        lambda m: MARK + m.group(1) + seed(LIGHT) + "," + m.group(2) + seed(DARK),
        s, "default seeds")

    # 2. Status colors (first table = dark, second = light).
    def status(c, code):
        return '{error:"%s",warning:"%s",link:"%s",success:"%s",code:"%s"}' % (
            c["error"], c["warning"], c["link"], c["success"], code)
    s = sub_once(
        r'(const [\w$]+=)\{error:"#de5555",warning:"#f3c949",link:"#6a9fcb",success:"#7aae66",code:"#d7ba7d"\}'
        r',([\w$]+=)\{error:"#f05151",warning:"#ac830b",link:"#3e8ed1",success:"#58983f",code:"#a31515"\}',
        lambda m: m.group(1) + status(DARK_STATUS, "#d7ba7d") + "," + m.group(2) + status(LIGHT_STATUS, "#a31515"),
        s, "status colors")

    # 3. Theme picker presets.
    s = sub_once(
        r'"Default Light":\{background:"#F9F9F9",foregroundOverride:"#101010",primary:"#007acc"\}',
        lambda m: '"Default Light":' + preset(LIGHT)
        + ',"Classic Light":{background:"#F9F9F9",foregroundOverride:"#101010",primary:"#007acc"}',
        s, "light presets")
    s = sub_once(
        r'"Default Dark":\{background:"#101010",foregroundOverride:"#cccccc",\s*primary:"#007acc"\}',
        lambda m: '"Default Dark":' + preset(DARK)
        + ',"Classic Dark":{background:"#101010",foregroundOverride:"#cccccc",primary:"#007acc"}',
        s, "dark presets")

    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    print("[theme-patch] DeltaMod theme applied")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: patch_theme.py <main.js>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])
