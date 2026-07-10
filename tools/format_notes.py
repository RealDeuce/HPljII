#!/usr/bin/env python3
"""Format notes Markdown and normalize ordinary changed-file whitespace."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import textwrap
from collections import defaultdict
from pathlib import Path


LIST_RE = re.compile(r"^(\s*(?:[-*+]|\d+[.])\s+)(.*)$")
INDENT_RE = re.compile(r"^([ \t]+)(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LOCAL_MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+\.md)#([^)]+)\)")
TAB_WIDTH = 8


def normalize_text_whitespace(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    normalized = []
    for line in lines:
        line = line.rstrip(" \t")
        match = INDENT_RE.match(line)
        if match and " \t" in match.group(1):
            indent, body = match.groups()
            column = 0
            for char in indent:
                if char == "\t":
                    column += TAB_WIDTH - (column % TAB_WIDTH)
                else:
                    column += 1
            line = (" " * column) + body
        normalized.append(line)
    return "\n".join(normalized).rstrip("\n") + "\n"


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_git_diff_check(root: Path) -> subprocess.CompletedProcess[str]:
    return run_git(root, ["diff", "--check", "HEAD"])


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


def changed_worktree_paths(root: Path) -> list[Path]:
    result = run_git(root, ["diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip())

    paths = {root / name for name in result.stdout.splitlines()}

    untracked = run_git(root, ["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        raise SystemExit(untracked.stderr.strip())
    paths.update(root / name for name in untracked.stdout.splitlines())

    return sorted(path for path in paths if path.exists() and path.is_file())


def is_text_file(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if b"\0" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


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

    return normalize_text_whitespace("\n".join(out))


HANDLED_DIFF_CHECK_ISSUES = {
    "trailing whitespace.",
    "space before tab in indent.",
    "new blank line at EOF.",
}


def diff_check_path_and_issue(line: str) -> tuple[str, str] | None:
    match = re.match(r"^([^:]+):\d+:\s*(.*)$", line)
    if match:
        return match.group(1), match.group(2)
    return None


def unhandled_diff_check_failures(
    root: Path,
    normalized_paths: list[Path],
) -> list[str]:
    result = run_git_diff_check(root)
    lines = [line for line in result.stdout.splitlines() if line]
    lines.extend(line for line in result.stderr.splitlines() if line)
    if result.returncode == 0:
        return []

    normalized_names = {str(path.relative_to(root)) for path in normalized_paths}
    failures = []
    for line in lines:
        parsed = diff_check_path_and_issue(line)
        if parsed is not None:
            name, issue = parsed
        else:
            name, issue = None, None
        if name in normalized_names and issue in HANDLED_DIFF_CHECK_ISSUES:
            continue
        failures.append(line)
    return failures


def heading_anchor(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text


def markdown_anchors(path: Path) -> set[str]:
    counts: defaultdict[str, int] = defaultdict(int)
    anchors = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = heading_anchor(match.group(2))
        index = counts[base]
        counts[base] += 1
        anchors.add(base if index == 0 else f"{base}-{index}")
    return anchors


def local_anchor_failures(root: Path, paths: list[Path]) -> list[str]:
    note_anchors: dict[Path, set[str]] = {}
    failures: list[str] = []

    for path in paths:
        rel_parent = path.parent
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in LOCAL_MD_LINK_RE.finditer(line):
                target_name, anchor = match.groups()
                if "://" in target_name:
                    continue
                target = (rel_parent / target_name).resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    continue
                if not target.exists():
                    failures.append(
                        f"{path.relative_to(root)}:{lineno}: missing linked file "
                        f"{target.relative_to(root)}"
                    )
                    continue
                if target not in note_anchors:
                    note_anchors[target] = markdown_anchors(target)
                if anchor not in note_anchors[target]:
                    failures.append(
                        f"{path.relative_to(root)}:{lineno}: missing anchor "
                        f"{target.relative_to(root)}#{anchor}"
                    )

    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Format notes Markdown by wrapping prose paragraphs, and normalize "
            "ordinary whitespace in changed text files. This is the formatting "
            "and whitespace gate: check mode also runs git diff --check HEAD "
            "internally and reports only issues the formatter could not repair."
        ),
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
        help=(
            "report files that would change and any unhandled git diff "
            "whitespace/conflict-marker failures; running without --check "
            "applies Markdown wrapping and changed text-file whitespace "
            "normalization"
        ),
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

    # `git diff --check HEAD` below checks the whole worktree diff, so the
    # matching repair pass has to cover the whole changed text set too.
    whitespace_paths = changed_worktree_paths(root)

    whitespace_changed: list[Path] = []
    for path in whitespace_paths:
        if not is_text_file(path):
            continue
        original = path.read_text(encoding="utf-8")
        normalized = normalize_text_whitespace(original)
        if normalized != original:
            whitespace_changed.append(path)
            if not args.check:
                path.write_text(normalized, encoding="utf-8")

    failures: list[str] = []

    if args.check and changed:
        failures.extend(f"would format {path.relative_to(root)}" for path in changed)

    if args.check and whitespace_changed:
        failures.extend(
            f"would normalize whitespace {path.relative_to(root)}"
            for path in whitespace_changed
            if path not in changed
        )

    if args.check:
        failures.extend(local_anchor_failures(root, paths))

    failures.extend(unhandled_diff_check_failures(root, whitespace_changed))

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    action = "would format" if args.check else "formatted"
    reported = False
    if changed:
        for path in changed:
            print(f"{action} {path.relative_to(root)}")
            reported = True
    if whitespace_changed:
        for path in whitespace_changed:
            if path not in changed:
                print(f"{action} whitespace {path.relative_to(root)}")
                reported = True
    if not reported:
        print("ok: no formatting or whitespace-gate changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
