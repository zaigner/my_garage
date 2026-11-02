"""CLI: ``record-tutorials [video ...]`` (no names records every video)."""

from __future__ import annotations

import sys

from .flows import FLOWS


def main(argv: list[str]) -> int:
    names = argv or list(FLOWS)
    unknown = [n for n in names if n not in FLOWS]
    if unknown:
        print(
            f"Unknown video(s): {', '.join(unknown)}. Valid names: {', '.join(FLOWS)}",
            file=sys.stderr,
        )
        return 2
    from . import harness  # lazy: keeps the CLI importable without Playwright

    try:
        return harness.run(names)
    except Exception as exc:
        print(f"ERROR: recording failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
