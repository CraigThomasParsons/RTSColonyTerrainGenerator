"""CLI for the artifact hash tool.

  python -m tools.artifact_hash hash <path> [--ignore-identity]
  python -m tools.artifact_hash manifest <job_id> [--out <file>]

Run from the repository root.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .hasher import build_manifest, logical_hash


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.artifact_hash", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_hash = sub.add_parser("hash", help="print the logical hash of one artifact")
    p_hash.add_argument("path")
    p_hash.add_argument("--ignore-identity", action="store_true",
                        help="also strip job_id so different runs of the same map match")

    p_manifest = sub.add_parser("manifest", help="build a logical-hash manifest for a completed job")
    p_manifest.add_argument("job_id")
    p_manifest.add_argument("--out", help="write JSON here instead of stdout")
    p_manifest.add_argument("--repo-root", default=".", help="repository root (default: cwd)")

    args = parser.parse_args(argv)

    if args.command == "hash":
        print(logical_hash(args.path, ignore_identity=args.ignore_identity))
        return 0

    if args.command == "manifest":
        manifest = build_manifest(args.job_id, args.repo_root)
        text = json.dumps(manifest, indent=2, sort_keys=True)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
            print(f"wrote {args.out} ({len(manifest['artifacts'])} artifacts, "
                  f"{len(manifest['missing'])} missing)")
        else:
            print(text)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
