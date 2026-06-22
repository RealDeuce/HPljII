#!/usr/bin/env python3
"""Format notes Markdown into patch-friendly wrapped prose."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import textwrap
from pathlib import Path


LIST_RE = re.compile(r"^(\s*(?:[-*+]|\d+[.])\s+)(.*)$")


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def repo_root() -> Path:
    result = run_git(Path.cwd(), ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "not inside a git repository")
    return Path(result.stdout.strip())


def changed_note_markdown(root: Path) -> list[Path]:
    result = run_git(
        root,
        ["diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "--", "notes"],
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip())

    paths = {root / name for name in result.stdout.splitlines() if name.endswith(".md")}

    untracked = run_git(root, ["ls-files", "--others", "--exclude-standard", "--", "notes"])
    if untracked.returncode != 0:
        raise SystemExit(untracked.stderr.strip())
    paths.update(root / name for name in untracked.stdout.splitlines() if name.endswith(".md"))

    return sorted(paths)


def all_note_markdown(root: Path) -> list[Path]:
    result = run_git(root, ["ls-files", "--", "notes/*.md"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip())

    paths = [root / name for name in result.stdout.splitlines()]
    untracked = run_git(root, ["ls-files", "--others", "--exclude-standard", "--", "notes"])
    if untracked.returncode != 0:
        raise SystemExit(untracked.stderr.strip())
    paths.extend(root / name for name in untracked.stdout.splitlines() if name.endswith(".md"))

    return sorted(set(paths))


def passthrough_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    if stripped.startswith(("```", "~~~")):
        return True
    if stripped.startswith((">", "<")):
        return True
    if stripped in {"---", "***", "___"}:
        return True
    if "|" in line:
        return True
    if re.match(r"^\s{4,}\S", line):
        return True
    return False


def wrap_plain(lines: list[str], width: int) -> list[str]:
    text = " ".join(line.strip() for line in lines)
    return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)


def wrap_list(lines: list[str], width: int) -> list[str]:
    match = LIST_RE.match(lines[0])
    if not match:
        return wrap_plain(lines, width)

    prefix, first = match.groups()
    body_parts = [first.strip()]
    body_parts.extend(line.strip() for line in lines[1:])
    body = " ".join(part for part in body_parts if part)
    continuation = " " * len(prefix)
    return textwrap.wrap(
        body,
        width=width,
        initial_indent=prefix,
        subsequent_indent=continuation,
        break_long_words=False,
        break_on_hyphens=False,
    )


def collect_paragraph(lines: list[str], start: int) -> tuple[list[str], int]:
    para = [lines[start]]
    i = start + 1
    list_item = LIST_RE.match(lines[start]) is not None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            break
        if passthrough_line(line):
            break
        if LIST_RE.match(line):
            break
        if list_item and not line.startswith(" "):
            break
        para.append(line)
        i += 1

    return para, i


def format_markdown(text: str, width: int) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    in_fence = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            out.append(line.rstrip())
            i += 1
            continue

        if in_fence or passthrough_line(line):
            out.append(line.rstrip())
            i += 1
            continue

        para, next_i = collect_paragraph(lines, i)
        if all(len(item) <= width for item in para):
            out.extend(item.rstrip() for item in para)
        elif LIST_RE.match(para[0]):
            out.extend(wrap_list(para, width))
        else:
            out.extend(wrap_plain(para, width))
        i = next_i

    result = "\n".join(out).rstrip() + "\n"
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Format notes Markdown by wrapping prose paragraphs.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="specific Markdown files to format",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="format all tracked and untracked Markdown files under notes/",
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help="format changed and untracked Markdown files under notes/",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=88,
        help="target prose wrap width, default: 88",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report files that would change and run git diff --check",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()

    if args.paths:
        paths = [
            (Path.cwd() / path).resolve() if not path.is_absolute() else path
            for path in args.paths
        ]
    elif args.all:
        paths = all_note_markdown(root)
    elif args.changed:
        paths = changed_note_markdown(root)
    else:
        print("format_notes.py: pass Markdown paths, --changed, or --all", file=sys.stderr)
        return 2

    paths = [path for path in paths if path.suffix == ".md" and path.exists()]
    changed: list[Path] = []

    for path in paths:
        original = path.read_text(encoding="utf-8")
        formatted = format_markdown(original, args.width)
        if formatted != original:
            changed.append(path)
            if not args.check:
                path.write_text(formatted, encoding="utf-8")

    failures: list[str] = []

    if args.check and changed:
        failures.extend(f"would format {path.relative_to(root)}" for path in changed)

    if args.check:
        for diff_args in (["diff", "--check"], ["diff", "--cached", "--check"]):
            diff_check = run_git(root, diff_args)
            if diff_check.returncode != 0:
                output = "\n".join(
                    part for part in [diff_check.stdout, diff_check.stderr] if part
                )
                failures.append(output.strip())

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    action = "would format" if args.check else "formatted"
    if changed:
        for path in changed:
            print(f"{action} {path.relative_to(root)}")
    else:
        print("ok: no formatting changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
