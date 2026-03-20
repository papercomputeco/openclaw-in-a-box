#!/usr/bin/env python3
"""Minimal agent that analyzes a directory and writes a summary.

This is a template agent -- replace the logic in analyze_directory()
and write_summary() with your domain-specific agent behavior.

Usage:
    python3 scripts/agent.py /path/to/dir [--output output/summary.md]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path


def analyze_directory(directory: str) -> dict:
    """Walk a directory and collect file statistics."""
    extensions: Counter[str] = Counter()
    total_files = 0
    total_lines = 0

    for root, _dirs, files in os.walk(directory):
        for fname in files:
            fpath = Path(root) / fname
            ext = fpath.suffix or "(no ext)"
            extensions[ext] += 1
            total_files += 1
            try:
                total_lines += len(fpath.read_text(errors="replace").splitlines())
            except (OSError, UnicodeDecodeError):
                pass

    return {
        "directory": directory,
        "total_files": total_files,
        "total_lines": total_lines,
        "extensions": dict(extensions),
    }


def write_summary(result: dict, output_path: str) -> None:
    """Write analysis results to a markdown file."""
    lines = [
        "# Directory Analysis",
        "",
        f"**Directory:** `{result['directory']}`",
        f"**Total files:** {result['total_files']}",
        f"**Total lines:** {result['total_lines']}",
        "",
        "## File Types",
        "",
    ]
    for ext, count in sorted(result["extensions"].items(), key=lambda x: -x[1]):
        lines.append(f"- `{ext}`: {count} files")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a directory")
    parser.add_argument("directory", help="Directory to analyze")
    parser.add_argument("--output", default="output/summary.md", help="Output file path")
    args = parser.parse_args()

    if not Path(args.directory).is_dir():
        print(f"Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing: {args.directory}")
    result = analyze_directory(args.directory)
    print(f"Found {result['total_files']} files, {result['total_lines']} lines")

    write_summary(result, args.output)
    print(f"Summary written to: {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()
