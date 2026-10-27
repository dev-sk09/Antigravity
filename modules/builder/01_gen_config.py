#!/usr/bin/env python3
"""
01_gen_config.py - Generates BuildConfig.java, gen.xml, and dev-aware AndroidManifest.xml.
"""
import sys
import os
import html
import shutil
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))


def parse_env(path):
    data = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def java_string(value):
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped + '"'


def main():
    build_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJECT_ROOT, "build")
    env_file = os.path.join(PROJECT_ROOT, "config", "app.env")
    env = parse_env(env_file)

    is_dev = os.environ.get("DEV_MODE") == "1"

    pkg_base = env.get("PKG", "com.agy")
    app_id = env.get("PKG_DEV", "com.agy.dev") if is_dev else pkg_base
    port = env.get("PORT_DEV", "45158") if is_dev else env.get("PORT", "45157")
    port_dev = env.get("PORT_DEV", "45158")
    gw_port = env.get("GATEWAY_PORT_DEV", "45161") if is_dev else env.get("GATEWAY_PORT", "45160")
    core_version = env.get("CORE_VERSION", "2.11.0")
    app_version_name = env.get("APP_VERSION_NAME", "2.4.0")
    app_version_code = env.get("APP_VERSION_CODE", "16")
    oauth_scheme = env.get("OAUTH_SCHEME", "antigravity")
    app_name = env.get("APP_NAME_DEV", "Antigravity Dev") if is_dev else env.get("APP_NAME", "Antigravity")
    min_api = env.get("MIN_API", "24")
    target_sdk = env.get("TARGET_SDK", "28")
    is_debug = "true" if is_dev else "false"

    pkg_dir = os.path.join(build_dir, "gen", *pkg_base.split("."))
    res_values_dir = os.path.join(build_dir, "res", "values")
    os.makedirs(pkg_dir, exist_ok=True)
    os.makedirs(res_values_dir, exist_ok=True)

    # 1. BuildConfig.java (always in com.agy package for source compatibility)
    agy_pkg_dir = os.path.join(build_dir, "gen", "com", "agy")
    os.makedirs(agy_pkg_dir, exist_ok=True)
    build_config_code = (
        "package com.agy;\n\n"
        "public final class BuildConfig {\n"
        "    private BuildConfig() {}\n\n"
        "    public static final String APPLICATION_ID = %s;\n"
        "    public static final int PORT = %s;\n"
        "    public static final int PORT_DEV = %s;\n"
        "    public static final int GATEWAY_PORT = %s;\n"
        "    public static final String CORE_VERSION = %s;\n"
        "    public static final String APP_VERSION_NAME = %s;\n"
        "    public static final int APP_VERSION_CODE = %s;\n"
        "    public static final String OAUTH_SCHEME = %s;\n"
        "    public static final String APP_NAME = %s;\n"
        "    public static final int MIN_API = %s;\n"
        "    public static final int TARGET_SDK = %s;\n"
        "    public static final boolean DEBUG = %s;\n"
        "}\n"
    ) % (
        java_string(app_id),
        port,
        port_dev,
        gw_port,
        java_string(core_version),
        java_string(app_version_name),
        app_version_code,
        java_string(oauth_scheme),
        java_string(app_name),
        min_api,
        target_sdk,
        is_debug,
    )
    build_config_path = os.path.join(agy_pkg_dir, "BuildConfig.java")
    with open(build_config_path, "w", encoding="utf-8") as f:
        f.write(build_config_code)

    if pkg_base != "com.agy":
        custom_pkg_dir = os.path.join(build_dir, "gen", *pkg_base.split("."))
        os.makedirs(custom_pkg_dir, exist_ok=True)
        with open(os.path.join(custom_pkg_dir, "BuildConfig.java"), "w", encoding="utf-8") as f:
            f.write(build_config_code.replace("package com.agy;", f"package {pkg_base};"))

    # 2. gen.xml
    gen_xml_path = os.path.join(res_values_dir, "gen.xml")
    with open(gen_xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write("<resources>\n")
        f.write('    <string name="app_name">%s</string>\n' % html.escape(app_name, quote=True))
        f.write('    <integer name="https_server_port">%s</integer>\n' % port)
        f.write('    <integer name="gateway_port">%s</integer>\n' % gw_port)
        f.write('    <string name="oauth_scheme">%s</string>\n' % html.escape(oauth_scheme, quote=True))
        f.write("</resources>\n")

    # 3. AndroidManifest.xml (dev-aware)
    src_manifest = os.path.join(PROJECT_ROOT, "app", "src", "main", "AndroidManifest.xml")
    target_manifest = os.path.join(build_dir, "AndroidManifest.xml")
    with open(src_manifest, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace('${applicationId}', app_id)
    content = re.sub(r'android:versionName="[^"]+"', f'android:versionName="{app_version_name}"', content)
    content = re.sub(r'android:versionCode="[^"]+"', f'android:versionCode="{app_version_code}"', content)

    if is_dev:
        content = content.replace('package="com.agy"', 'package="com.agy.dev"')
        content = content.replace('com.agy.permission.INTERNAL_BROADCAST', 'com.agy.dev.permission.INTERNAL_BROADCAST')
        content = content.replace('<application', '<application android:debuggable="true"')
        print(f"[*] Configured DEV manifest: package=com.agy.dev, debuggable=true")

    with open(target_manifest, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] Generated BuildConfig.java -> {build_config_path}")
    print(f"[OK] Generated gen.xml -> {gen_xml_path}")
    print(f"[OK] Generated manifest -> {target_manifest}")


if __name__ == "__main__":
    main()
