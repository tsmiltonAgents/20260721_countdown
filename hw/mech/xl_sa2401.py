"""XL-SA2401SRWC 4-digit 7-seg display — cosmetic render model.
Origin: body centre at board surface (KiCad footprint origin), +Z up.
"""
from build123d import (Box, Color, Compound, Location, Pos)


def gen_step():
    parts = []

    base = Box(28.5, 10.0, 2.2)
    base = Pos(0, 0, 1.1) * base
    base.label = "body_base"
    base.color = Color(0.35, 0.35, 0.33)
    parts.append(base)

    lens = Box(28.5, 10.0, 0.8)
    lens = Pos(0, 0, 2.2 + 0.4) * lens
    lens.label = "lens"
    lens.color = Color(0.25, 0.02, 0.02)
    parts.append(lens)

    # digit windows: slightly proud dark-red glass look
    for i in range(4):
        cx = -8.325 + i * 5.55
        win = Box(4.2, 7.4, 0.1)
        win = Pos(cx, 0, 3.0) * win
        win.label = f"digit_{i+1}"
        win.color = Color(0.45, 0.05, 0.05)
        parts.append(win)

    # wrap pads: 12 signal on 2.54 pitch + 4 anchors at +/-11.43
    pad_xs = [-6.35 + k * 2.54 for k in range(6)]
    for y in (-4.95, 4.95):
        for x in pad_xs:
            pad = Box(1.5, 0.25, 1.5)
            pad = Pos(x, y, 0.75) * pad
            pad.label = "pad"
            pad.color = Color(0.83, 0.82, 0.78)
            parts.append(pad)
        for x in (-11.43, 11.43):
            pad = Box(2.0, 0.25, 1.5)
            pad = Pos(x, y, 0.75) * pad
            pad.label = "anchor"
            pad.color = Color(0.83, 0.82, 0.78)
            parts.append(pad)

    asm = Compound(children=parts)
    asm.label = "XL-SA2401SRWC"
    return asm
