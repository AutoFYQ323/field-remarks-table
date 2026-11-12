# -*- coding: utf-8 -*-
"""Build plugins.qgis.org upload ZIP (top folder attribute_table/)."""
import os
import zipfile

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(PLUGIN_DIR)
PLUGIN_NAME = "attribute_table"
TEST_DIR = os.path.join(REPO_ROOT, "TEST")


def _release_version():
    meta = os.path.join(PLUGIN_DIR, "metadata.txt")
    if not os.path.isfile(meta):
        return "0.0.0"
    with open(meta, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("version="):
                return line.split("=", 1)[1].strip()
    return "0.0.0"


SKIP_DIRS = {".git", "__pycache__", ".cursor", ".vscode"}
SKIP_FILES = {
    ".bandit",
    ".flake8",
    ".secrets.baseline",
    "setup.cfg",
    "tox.ini",
    "_make_release_zip.py",
    "_bandit_fix.py",
    "check_i18n.py",
}
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
    os.makedirs(TEST_DIR, exist_ok=True)
    out_path = os.path.join(TEST_DIR, "attribute_table-%s.zip" % _release_version())
    if os.path.isfile(out_path):
        os.remove(out_path)
    count = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
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
    size = os.path.getsize(out_path)
    print("Wrote:", out_path)
    print("Files:", count)
    print("Size bytes:", size)
    print("Size MB:", round(size / (1024 * 1024), 2))


if __name__ == "__main__":
    main()
