"""MYOUNG BS-08-B2AA001 CR2032 holder — cosmetic render model.
Origin: cavity centre at board surface, +Z up. Mouth faces -X.
"""
from build123d import (Box, Color, Compound, Cylinder, Location, Mode, Pos,
                       Rot, extrude, Circle, Plane)


def gen_step():
    parts = []

    # main ring: outer 22.3, inner 20.3, h 5.3
    ring = Cylinder(radius=11.15, height=5.3) - Cylinder(radius=10.15, height=5.3)
    ring = Pos(0, 0, 2.65) * ring
    # retainer lip: top 1.0 mm overhangs inward to 19.0
    lip = Cylinder(radius=11.15, height=1.0) - Cylinder(radius=9.5, height=1.0)
    lip = Pos(0, 0, 4.8) * lip
    body = ring + lip
    # mouth: 100-degree wedge on -X above z=1.5
    wedge = Box(14, 18, 5.4)
    wedge = Pos(-13.2, 0, 1.5 + 2.7) * wedge
    body = body - wedge
    body.label = "holder_body"
    body.color = Color(0.45, 0.30, 0.18)
    parts.append(body)

    # (+) terminal tab to x=+14.55
    tab = Box(4.55, 3.5, 0.2)
    tab = Pos(12.3, 0, 0.1) * tab
    tab.label = "pos_tab"
    tab.color = Color(0.85, 0.72, 0.35)
    parts.append(tab)

    # (-) spring tongues near centre
    for y in (-3.0, 3.0):
        spring = Box(3.5, 1.8, 0.2)
        spring = Pos(-2.5, y, 0.4) * spring
        spring.label = "neg_spring"
        spring.color = Color(0.85, 0.72, 0.35)
        parts.append(spring)

    asm = Compound(children=parts)
    asm.label = "BS-08-B2AA001"
    return asm
