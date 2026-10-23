# -*- coding: utf-8 -*-
"""Fail when a plugin UI string has no Spanish, French, or Arabic line.

Run from the plugin folder:

    python check_i18n.py

_make_release_zip.py runs this before it writes the zip. Packing the folder
by hand in the file manager does not run it.
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LANGS = ("es", "fr", "ar")
SKIP_PARTS = {"__pycache__", "locales"}
SKIP_FILES = {
    "messages_en.py",
    "messages_en_extra.py",
    "catalog.py",
    "help_en.py",
    "help_es.py",
    "help_fr.py",
    "help_ar.py",
    "check_i18n.py",
}
_PCT = re.compile(r"%(?!%)(?:\([^)]+\))?[#0\- +]*\d*(?:\.\d+)?[diouxXeEfFgGcrs]")
_BRACE = re.compile(r"\{[^{}]*\}")


def _load_assign(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise SystemExit("missing %s in %s" % (name, path.name))


def _load_locale(path):
    """Locale modules only build a dict. They are not imported as a package."""
    ns = {"__builtins__": {}}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns, ns)  # nosec B102
    text = ns.get("TEXT")
    if not isinstance(text, dict):
        raise SystemExit("%s has no TEXT dict" % path.name)
    return text


def english_catalog():
    en = {}
    en.update(_load_assign(ROOT / "i18n" / "messages_en.py", "EN"))
    en.update(_load_assign(ROOT / "i18n" / "messages_en_extra.py", "EXTRA"))
    return en


def _tr_strings(tree):
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != "tr":
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            found.append(arg.value)
    return found


def _constants(tree):
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append(node.value)
    return found


def source_files():
    for path in ROOT.rglob("*.py"):
        if SKIP_PARTS.intersection(path.parts) or path.name in SKIP_FILES:
            continue
        yield path


def required_keys(english):
    keys = set()
    for path in source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for text in _tr_strings(tree):
            keys.add(text)
        for text in _constants(tree):
            if text in english:
                keys.add(text)
    return keys


def signature(text):
    # {{title}} is the pack-variable syntax, not a str.format field.
    shielded = re.sub(r"\{\{[^{}]*\}\}", "VAR", text)
    return (_PCT.findall(text), _BRACE.findall(shielded))


def check_help():
    problems = []
    for lang, filename in (
        ("zh", "help_pages.py"),
        ("en", "help_pages.py"),
        ("es", "help_es.py"),
        ("fr", "help_fr.py"),
        ("ar", "help_ar.py"),
    ):
        path = ROOT / "i18n" / filename
        if not path.is_file():
            problems.append("%s help file is missing" % lang)
            continue
        name = "PAGES_ZH" if lang == "zh" else "PAGES_EN" if lang == "en" else "PAGES"
        try:
            pages = _load_assign(path, name)
        except SystemExit:
            problems.append("%s help has no %s" % (lang, name))
            continue
        if len(pages) != 5:
            problems.append("%s help has %s pages, expected 5" % (lang, len(pages)))
            continue
        for title, html in pages:
            if not str(title).strip():
                problems.append("%s help has an empty page title" % lang)
            if "<h3>" not in str(html):
                problems.append("%s help page %r has no heading" % (lang, title))
    return problems


def main():
    english = english_catalog()
    problems = []
    keys = required_keys(english)
    missing_en = sorted(key for key in keys if key not in english)
    for key in missing_en:
        problems.append("EN missing: %s" % key)
    catalogs = {}
    for lang in LANGS:
        path = ROOT / "i18n" / "locales" / ("%s.py" % lang)
        if not path.is_file():
            problems.append("%s catalog is missing" % lang)
            continue
        catalogs[lang] = _load_locale(path)
    for key in sorted(keys):
        if key not in english:
            continue
        src_sig = signature(key)
        en_sig = signature(english[key])
        if src_sig != en_sig:
            problems.append("EN placeholders differ: %s" % key)
        for lang, table in catalogs.items():
            if key not in table or not str(table[key]).strip():
                problems.append("%s missing: %s" % (lang.upper(), key))
                continue
            if signature(table[key]) != src_sig:
                problems.append("%s placeholders differ: %s" % (lang.upper(), key))
            if table[key] == key and english[key] != key:
                problems.append("%s still Chinese: %s" % (lang.upper(), key))
    problems.extend(check_help())
    if problems:
        sys.stdout.write("i18n check failed: %s\n" % len(problems))
        sys.stdout.write("\n".join(problems[:80]))
        if len(problems) > 80:
            sys.stdout.write("\n... %s more\n" % (len(problems) - 80))
        else:
            sys.stdout.write("\n")
        return 1
    sys.stdout.write("i18n check ok: %s strings, es/fr/ar, 5 help pages\n" % len(keys))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
