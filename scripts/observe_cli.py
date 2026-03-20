#!/usr/bin/env python3
"""CLI for running the observation extractor.

Usage:
    python3 scripts/observe_cli.py [--db PATH] [--dry-run] [--reset]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from observer import Observer


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract observations from Tapes sessions")
    parser.add_argument("--db", default=".tapes/tapes.sqlite", help="Path to tapes.sqlite")
    parser.add_argument("--memory-dir", default=".tapes/memory", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--reset", action="store_true", help="Reprocess all sessions")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Tapes database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    memory_dir = Path(args.memory_dir)
    memory_dir.mkdir(parents=True, exist_ok=True)

    if args.reset:
        state_file = memory_dir / "observer_state.json"
        if state_file.exists():
            state_file.unlink()
            print("Reset watermark -- will reprocess all sessions")

    obs = Observer(str(db_path), str(memory_dir))

    if args.dry_run:
        sessions = obs.get_unprocessed_sessions()
        for sid in sessions:
            session = obs.reader.read_session(sid)
            observations = obs.observe_session(session)
            for o in observations:
                print(f"  [{o.priority}] {o.content[:80]}")
        print(f"\nDry run: {len(sessions)} sessions, would extract observations")
    else:
        observations = obs.run()
        if not observations:
            print("No new observations found.")
        else:
            for o in observations:
                print(f"  [{o.priority}] {o.content[:80]}")
            print(f"\nWrote {len(observations)} observations to {memory_dir / 'observations.md'}")


if __name__ == "__main__":
    main()
