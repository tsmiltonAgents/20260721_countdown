"""CR2032 coin cell — cosmetic model for populated renders.
Origin: centre of underside at board-facing plane, +Z up.
"""
from build123d import Color, Compound, Cylinder, Pos, chamfer


def gen_step():
    cell = Cylinder(radius=10.0, height=3.2)
    cell = Pos(0, 0, 1.6) * cell
    top_edge = cell.edges().group_by(lambda e: e.center().Z)[-1]
    cell = chamfer(top_edge, 0.4)
    cell.label = "cr2032"
    cell.color = Color(0.78, 0.78, 0.80)
    asm = Compound(children=[cell])
    asm.label = "CR2032"
    return asm
