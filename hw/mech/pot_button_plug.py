"""TPU button plug: sits in the mold-floor seat, presses lightly against
the switch plunger, and leaves an open finger well over the button after
demolding. Print in TPU (or cast silicone) so it releases cleanly.

Height budget: the down-facing switch plunger sits 1.5 mm above the mold
floor (board front rests on the 3.0 mm display; switch is 1.5 tall). The
plug tops out at 1.40 mm — a deliberate 0.1 mm gap so the switch is NOT
held pressed during the cure (a pressed button would run the MCU/display
for the whole cure and drain the sealed-in cell). The resulting ~0.1 mm
resin flash film over the plunger cracks away on first use.
"""
from build123d import Color, Compound, Cone, Cylinder, Pos


def gen_step():
    base = Cylinder(radius=3.0, height=0.4)      # sits in the seat recess
    base = Pos(0, 0, 0.2) * base
    cone = Cone(bottom_radius=3.0, top_radius=2.4, height=1.0)
    cone = Pos(0, 0, 0.4 + 0.5) * cone
    plug = base + cone
    plug.label = "button_plug"
    plug.color = Color(0.9, 0.4, 0.2)
    asm = Compound(children=[plug])
    asm.label = "T-MINUS button plug"
    return asm
