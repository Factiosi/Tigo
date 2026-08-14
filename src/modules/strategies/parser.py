"""Parse winws.exe arguments from flowseal .bat strategy files."""

from __future__ import annotations

import re
from pathlib import Path

ARGS_WITH_VALUE = frozenset({"sni", "host", "altorder"})
BAT_LINE_CONTINUATION = re.compile(r"\^\s*$")


def _tokenize_batch_line(line: str) -> list[str]:
    """Tokenize a batch line similarly to `for %%i in (!line!)`."""
    line = line.strip()
    if not line:
        return []

    tokens: list[str] = []
    current = ""
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            in_quotes = not in_quotes
            current += ch
        elif ch.isspace() and not in_quotes:
            if current:
                tokens.append(current)
                current = ""
        else:
            current += ch
        i += 1
    if current:
        tokens.append(current)
    return tokens


def _merge_tokens(tokens: list[str]) -> str:
    """Port of service.bat mergeargs logic (lines 296-337)."""
    mergeargs = 0
    parts: list[str] = []

    for raw in tokens:
        arg = raw
        if arg in ("^", "^^"):
            continue

        if arg.startswith("--") and mergeargs != 0:
            mergeargs = 0

        if arg.startswith('"') and arg.endswith('"') and len(arg) >= 2:
            inner = arg[1:-1]
            if ":" in inner:
                arg = f'\\"{inner}\\"'
            elif inner.startswith("@"):
                arg = f'\\"@%~dp0{inner[1:]}\\"'
            else:
                arg = f'\\"%~dp0{inner}\\"'

        if mergeargs == 1:
            parts[-1] = f"{parts[-1]},{arg}"
        elif mergeargs == 3:
            parts[-1] = f"{parts[-1]}={arg}"
            mergeargs = 1
        else:
            parts.append(arg)

        if arg.startswith("--"):
            mergeargs = 2
        elif mergeargs >= 1:
            if mergeargs == 2:
                mergeargs = 1
            key = arg.lstrip("-").split("=", 1)[0].lower()
            if key in ARGS_WITH_VALUE:
                mergeargs = 3

    return " ".join(parts)


def _normalize_placeholders(args: str) -> str:
    """Keep flowseal placeholders for runtime resolution."""
    args = args.replace("EXCL_MARK", "!")
    args = args.strip().strip('"')
    args = re.sub(r'\\"%~dp0([^"\\]+)\\"', r'"%BIN%\\1"', args)
    args = re.sub(r'\\"@%~dp0([^"\\]+)\\"', r'"@%BIN%\\1"', args)
    args = args.replace("\\\"", '"')
    args = args.replace("%~dp0", "%ROOT%")
    return " ".join(args.split())


def parse_bat_file(bat_path: Path) -> str:
    """Extract winws.exe argument string from a strategy .bat file."""
    text = bat_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    capture = False
    chunks: list[str] = []

    for raw_line in lines:
        line = raw_line.replace("^!", "EXCL_MARK")
        if "winws.exe" in line.lower():
            capture = True
            lower = line.lower()
            idx = lower.index("winws.exe")
            line = line[idx + len("winws.exe") :]
            line = line.lstrip().lstrip('"').lstrip()

        if not capture:
            continue

        line = BAT_LINE_CONTINUATION.sub("", line).strip()
        if not line:
            continue
        chunks.append(line)

    if not chunks:
        raise ValueError(f"No winws.exe invocation found in {bat_path.name}")

    combined = " ".join(chunks)
    tokens = _tokenize_batch_line(combined)
    merged = _merge_tokens(tokens)
    return _normalize_placeholders(merged)


def list_strategy_bats(root: Path) -> list[Path]:
    bats = [
        p
        for p in root.glob("*.bat")
        if p.is_file() and not p.name.lower().startswith("service")
    ]
    return sorted(bats, key=lambda p: p.name.lower())


def convert_bat_to_strategy_text(bat_path: Path) -> str:
    args = parse_bat_file(bat_path)
    header = f"# source: {bat_path.name}\n"
    return header + args + "\n"


def read_strategy_args(strategy_path: Path) -> str:
    text = strategy_path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        raise ValueError(f"Strategy file is empty: {strategy_path}")
    return " ".join(lines)


def resolve_strategy_args(
    args_template: str,
    *,
    bin_dir: Path,
    lists_dir: Path,
    user_lists_dir: Path,
    root_dir: Path,
    game_filter_tcp: str,
    game_filter_udp: str,
) -> str:
    """Substitute placeholders for Windows service binPath."""
    result = args_template
    replacements = {
        "%BIN%": str(bin_dir).rstrip("\\/") + "\\",
        "%LISTS%": str(lists_dir).rstrip("\\/") + "\\",
        "%ROOT%": str(root_dir).rstrip("\\/") + "\\",
        "%GameFilterTCP%": game_filter_tcp,
        "%GameFilterUDP%": game_filter_udp,
    }
    for key, value in replacements.items():
        result = result.replace(key, value)

    for user_file in (
        "list-general-user.txt",
        "list-exclude-user.txt",
        "ipset-exclude-user.txt",
    ):
        src = str(user_lists_dir / user_file).replace("/", "\\")
        result = result.replace(f"{replacements['%LISTS%']}{user_file}", src)

    return result.strip()
