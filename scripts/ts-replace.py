#!/usr/bin/env python3
"""TS/JS-aware string replacement for fix scripts.

Handles the escape-mismatch problem: Python literal 'Fra Angelico's' does not
match TS source 'Fra Angelico\\'s' (escaped single-quote inside a
single-quoted string). This utility normalizes JS string-escape variants on
both sides before matching, so script authors can write the natural prose
without thinking about escapes.

Usage (library):
    from ts_replace import ts_replace
    n = ts_replace(path, "Fra Angelico's hand alone", "Fra Angelico alone")
    # n = 1 if replaced, 0 if not found

Usage (CLI):
    python3 ts-replace.py FILE 'old text' 'new text'

The matcher tries, in order:
    1. Literal match (the input strings as written)
    2. Both sides with apostrophes JS-escaped (X' -> X\\')
    3. Both sides with apostrophes JS-escaped AND smart-quote variants normalized

If the file contains the input string in multiple forms (e.g. once with
smart quotes, once with straight), only the first form found is replaced
and a warning is printed.

Designed for bulk fix scripts that hit ~10% MISS rate due to escape mismatch.
"""
import pathlib
import sys


SMART_QUOTE_MAP = str.maketrans({
    "‘": "'",  # left single quotation mark
    "’": "'",  # right single quotation mark
    "“": '"',  # left double quotation mark
    "”": '"',  # right double quotation mark
})


def _js_escape_in_single_quoted(s: str) -> str:
    """Escape apostrophes inside what would be a single-quoted JS string."""
    return s.replace("'", "\\'")


def _js_escape_in_double_quoted(s: str) -> str:
    """Escape double-quotes inside what would be a double-quoted JS string."""
    return s.replace('"', '\\"')


def _candidates(s: str):
    """Yield matching candidate forms for s, ordered by specificity."""
    yield s
    if "'" in s:
        yield _js_escape_in_single_quoted(s)
    if '"' in s:
        yield _js_escape_in_double_quoted(s)
    smart = s.translate({0x2019: "’", 0x2018: "‘"})
    if smart != s:
        yield smart


def ts_replace(path: pathlib.Path, old: str, new: str) -> int:
    """Replace `old` with `new` in `path`, trying JS-escape variants on both sides.

    Returns the number of replacements (0 or 1). Always single replacement
    semantics — multi-occurrence is a bug we want to surface, not silently
    flatten.
    """
    text = path.read_text()
    # Try each candidate form of `old` against the text
    for old_form in _candidates(old):
        if old_form in text:
            # Match found — apply with the corresponding new form (same escape policy)
            if old_form == old:
                new_form = new
            elif old_form == _js_escape_in_single_quoted(old):
                new_form = _js_escape_in_single_quoted(new)
            elif old_form == _js_escape_in_double_quoted(old):
                new_form = _js_escape_in_double_quoted(new)
            else:
                new_form = new
            # Sanity check uniqueness
            count = text.count(old_form)
            if count > 1:
                print(f"WARN {path.name}: '{old_form[:50]}...' found {count}× — replacing first only", file=sys.stderr)
            text = text.replace(old_form, new_form, 1)
            path.write_text(text)
            return 1
    return 0


def main():
    if len(sys.argv) != 4:
        print("Usage: ts-replace.py FILE 'old text' 'new text'", file=sys.stderr)
        sys.exit(2)
    path = pathlib.Path(sys.argv[1])
    if not path.exists():
        print(f"MISS: {path} does not exist", file=sys.stderr)
        sys.exit(1)
    n = ts_replace(path, sys.argv[2], sys.argv[3])
    print(f"{'OK  ' if n else 'MISS'} {path.name}")
    sys.exit(0 if n else 1)


if __name__ == "__main__":
    main()
