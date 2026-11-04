"""ffmpeg encoding, poster extraction and the size budget."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .variants import Variant

FPS = 20
CRF = 26
SIZE_BUDGET_BYTES = 6 * 1024 * 1024


class BudgetError(RuntimeError):
    """The committed MP4s together exceed the size budget."""


def encode_args(src: Path, dst: Path, trim_s: float, variant: Variant) -> list[str]:
    """ffmpeg argv turning Playwright's WebM into an iOS-safe H.264 MP4."""
    return [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{trim_s:.2f}",
        "-i",
        str(src),
        "-vf",
        f"scale={variant.width}:{variant.height}:flags=lanczos,fps={FPS}",
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-preset",
        "slow",
        "-tune",
        "animation",
        "-crf",
        str(CRF),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        str(dst),
    ]


def poster_args(src_mp4: Path, dst: Path, at_s: float) -> list[str]:
    """ffmpeg argv extracting one JPEG frame at ``at_s`` seconds."""
    return [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{at_s:.2f}",
        "-i",
        str(src_mp4),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(dst),
    ]


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run(args, check=True)


def total_mp4_bytes(out_dir: Path) -> int:
    return sum(p.stat().st_size for p in out_dir.glob("*.mp4"))


def check_budget(out_dir: Path, limit: int = SIZE_BUDGET_BYTES) -> int:
    """Return the MP4 total; raise BudgetError when it exceeds ``limit``."""
    total = total_mp4_bytes(out_dir)
    if total > limit:
        raise BudgetError(
            f"MP4s in {out_dir} total {total / 1024 / 1024:.2f} MB, "
            f"over the {limit / 1024 / 1024:.0f} MB budget"
        )
    return total
