"""Recording profiles: one phone, one desktop. Same flow, different frame."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Variant:
    name: str
    width: int
    height: int
    suffix: str  # appended to the video name in output file names
    verb: str  # "Tap" / "Click" in caption copy
    cursor_start: tuple[int, int]

    @property
    def viewport(self) -> dict[str, int]:
        return {"width": self.width, "height": self.height}

    @property
    def center(self) -> tuple[float, float]:
        return (self.width / 2, self.height / 2)


PHONE = Variant("phone", 390, 844, "", "Tap", (195, 700))
# At least 768px wide: that is the `md` breakpoint where grids and headers change.
DESKTOP = Variant("desktop", 880, 680, "-desktop", "Click", (440, 600))

VARIANTS = (PHONE, DESKTOP)
