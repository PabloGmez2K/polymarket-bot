#!/usr/bin/env python3
"""Validate Python syntax without writing .pyc files."""

from __future__ import annotations

import argparse
import pathlib
import sys


def _check_file(path_str: str) -> tuple[bool, str]:
    path = pathlib.Path(path_str)
    try:
        source = path.read_text(encoding="utf-8")
    except Exception as exc:
        return False, f"{path}: read failed: {exc}"

    try:
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        location = f"{path}:{exc.lineno}:{exc.offset}"
        return False, f"{location}: {exc.msg}"
    except Exception as exc:
        return False, f"{path}: compile failed: {exc}"

    return True, f"{path}: syntax ok"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Python syntax without generating __pycache__ artifacts."
    )
    parser.add_argument("paths", nargs="+", help="Python files to validate")
    args = parser.parse_args()

    failed = False
    for path_str in args.paths:
        ok, message = _check_file(path_str)
        print(message)
        failed = failed or (not ok)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
