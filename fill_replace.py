# -*- coding: utf-8 -*-
"""Replace one cell the way field processing does.

Three placements, independent of what is written:
- standard: change only the matched span, every match in the cell
- around: insert before or after each match and keep the original text
- field: if the cell matches, replace the whole cell

Matching is partial unless exact is set. An empty keyword matches nothing.
"""

import re

MODE_STANDARD = "standard"
MODE_AROUND = "around"
MODE_FIELD = "field"

SIDE_BEFORE = "before"
SIDE_AFTER = "after"


def match_spans(text, keyword, exact=False, case_sensitive=True):
    """Return [(start, end), ...] in order. Empty keyword matches nothing."""
    text = "" if text is None else str(text)
    keyword = "" if keyword is None else str(keyword)
    if exact:
        same = text == keyword if case_sensitive else text.lower() == keyword.lower()
        return [(0, len(text))] if same else []
    if keyword == "":
        return []
    if case_sensitive:
        spans = []
        start = 0
        step = max(len(keyword), 1)
        while True:
            found = text.find(keyword, start)
            if found < 0:
                break
            spans.append((found, found + len(keyword)))
            start = found + step
        return spans
    return [
        (match.start(), match.end())
        for match in re.finditer(re.escape(keyword), text, re.IGNORECASE)
    ]


def apply_replace(
    text,
    keyword,
    new_content,
    mode=MODE_STANDARD,
    side=SIDE_AFTER,
    exact=False,
    case_sensitive=True,
):
    """Return (new_text, hit_count). hit_count is 0 when the cell is unchanged by matching."""
    text = "" if text is None else str(text)
    new_content = "" if new_content is None else str(new_content)
    mode = mode or MODE_STANDARD
    side = side or SIDE_AFTER
    spans = match_spans(text, keyword, exact=exact, case_sensitive=case_sensitive)
    if not spans:
        return text, 0
    if mode == MODE_FIELD:
        return new_content, 1
    out = text
    if mode == MODE_AROUND and side == SIDE_BEFORE:
        for start, _end in reversed(spans):
            out = out[:start] + new_content + out[start:]
        return out, len(spans)
    if mode == MODE_AROUND:
        for _start, end in reversed(spans):
            out = out[:end] + new_content + out[end:]
        return out, len(spans)
    for start, end in reversed(spans):
        out = out[:start] + new_content + out[end:]
    return out, len(spans)
