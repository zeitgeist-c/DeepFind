"""Report missing UI translations and mixed-language fallbacks.

Turkish source text is the translation key. In any other language a key that
is missing from the table renders as Turkish (or as English in 'en'), which is
what a user sees as "the language flipped back". This tool lists those keys.

Usage:  PYTHONPATH=src python eval/i18n_audit.py [--limit N]
"""
from __future__ import annotations
import ast
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "deepfind"


def ui_strings():
    """Every literal passed as the first argument of t(...) in the source."""
    found = Counter()
    for path in SRC.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name != "t" or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found[first.value] += 1
    return found


def main():
    sys.path.insert(0, str(ROOT / "src"))
    from deepfind import theme

    limit = 40
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    strings = ui_strings()
    print(f"t() literals: {len(strings)}")
    for code, _name, _qt, _loc in theme.LANGUAGES:
        table = theme.TABLES.get(code) or {}
        missing = [s for s in strings if s not in table]
        # Turkish is the key language; it needs no table.
        ratio = 0.0 if not strings else 100.0 * (1 - len(missing) / len(strings))
        print(f"{code:6} covered {ratio:5.1f}%  missing {len(missing)}")
        for text in missing[:limit]:
            print(f"    - {text!r}")
        if len(missing) > limit:
            print(f"    ... {len(missing) - limit} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
