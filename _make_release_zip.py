# -*- coding: utf-8 -*-
"""Build plugins.qgis.org upload ZIP (top folder attribute_table/)."""
import os
import zipfile

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_NAME = "attribute_table"
OUT = os.path.join(os.path.dirname(PLUGIN_DIR), "attribute_table-1.18.7.zip")

SKIP_DIRS = {".git", "__pycache__", ".cursor", ".vscode"}
SKIP_FILES = {".bandit", "_make_release_zip.py", "_bandit_fix.py", "check_i18n.py"}
SKIP_SUFFIX = (".pyc", ".pyo")


def should_skip(rel_parts, name):
    if name in SKIP_FILES:
        return True
    if name.endswith(SKIP_SUFFIX):
        return True
    for part in rel_parts:
        if part in SKIP_DIRS:
            return True
    return False


def main():
    import subprocess
    import sys

    check = os.path.join(PLUGIN_DIR, "check_i18n.py")
    result = subprocess.call([sys.executable, check])
    if result != 0:
        raise SystemExit(result)
    if os.path.isfile(OUT):
        os.remove(OUT)
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(PLUGIN_DIR):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, PLUGIN_DIR)
                parts = rel.replace("\\", "/").split("/")
                if should_skip(parts[:-1], name):
                    continue
                arc = "%s/%s" % (PLUGIN_NAME, rel.replace("\\", "/"))
                zf.write(full, arc)
                count += 1
    size = os.path.getsize(OUT)
    print("Wrote:", OUT)
    print("Files:", count)
    print("Size bytes:", size)
    print("Size MB:", round(size / (1024 * 1024), 2))


if __name__ == "__main__":
    main()
