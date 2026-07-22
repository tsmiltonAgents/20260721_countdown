"""Generate custom footprints (hw/lib/countdown.pretty).

Sources (dimensions verified by eye against datasheet drawings):
- XL-SA2401SRWC: XINGLIGHT datasheet p.4. Body 28.5x10x3.0. 6 signal pads/row
  on 2.54 mm pitch (span 12.7, centered), rows wrap the 10 mm edges; plus 2
  mechanical anchor pads/row at x = +/-11.43 (22.86 outer dim). Package pad
  metal ~2.0 wide x 1.5 tall. Pin 1 bottom-left; bottom row 1-6 L->R;
  top row 7-12 R->L (12 top-left). O1.5 mold marks under body: no F vias.
- BS-08-B2AA001: MYOUNG drawing MY-CP-0007. (-) pad 4.3x2.8, left edge at
  -10.95 from center; (+) pad 3.5x3.8 R1.3, right edge at +14.75. Body
  24.1x15.7, cell slides in from the (-) side (left).
- TS-1187A: XKB drawing. Pads: datasheet 1.0x0.75 at (+/-3.0, +/-1.875);
  drawn 1.2x0.9 at (+/-3.1, +/-1.875) for toe fillet, inner edges kept at
  datasheet 2.5. A/B = top edge pair (one contact), C/D = bottom (other).
"""
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "lib", "countdown.pretty")

MODEL = ('\t(model "{path}"\n\t\t(offset (xyz 0 0 0))\n'
         '\t\t(scale (xyz 1 1 1))\n\t\t(rotate (xyz 0 0 0))\n\t)\n')

HDR = '(footprint "{name}"\n\t(version 20240108)\n\t(generator "gen_footprints")\n\t(layer "F.Cu")\n\t(attr {attr})\n'


def prop(name, val, y, hide=True, layer="F.Fab"):
    h = "(hide yes)" if hide else ""
    return (f'\t(property "{name}" "{val}" (at 0 {y} 0) (layer "{layer}") {h}'
            f' (effects (font (size 1 1) (thickness 0.15))))\n')


def pad_smd(num, x, y, w, h, shape="roundrect", rr=0.25):
    rrs = f" (roundrect_rratio {rr})" if shape == "roundrect" else ""
    return (f'\t(pad "{num}" smd {shape} (at {x} {y}) (size {w} {h}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask"){rrs})\n')


def line(x1, y1, x2, y2, layer, w=0.12):
    return (f'\t(fp_line (start {x1} {y1}) (end {x2} {y2}) '
            f'(stroke (width {w}) (type solid)) (layer "{layer}"))\n')


def rect(x1, y1, x2, y2, layer, w=0.12):
    return (f'\t(fp_rect (start {x1} {y1}) (end {x2} {y2}) '
            f'(stroke (width {w}) (type solid)) (fill no) (layer "{layer}"))\n')


def circle(cx, cy, r, layer, w=0.12, fill="no"):
    return (f'\t(fp_circle (center {cx} {cy}) (end {cx + r} {cy}) '
            f'(stroke (width {w}) (type solid)) (fill {fill}) (layer "{layer}"))\n')


def text_fab(txt, x, y, size=0.7):
    return (f'\t(fp_text user "{txt}" (at {x} {y} 0) (layer "F.Fab") '
            f'(effects (font (size {size} {size}) (thickness 0.12))))\n')


def display():
    s = HDR.format(name="XL-SA2401SRWC", attr="smd")
    s += prop("Reference", "REF**", -6.5, hide=False, layer="F.SilkS")
    s += prop("Value", "XL-SA2401SRWC", 6.5)
    s += prop("Footprint", "", 8)
    s += prop("Datasheet", "", 8)
    s += prop("Description", "4-digit 0.2in 7-seg SMD red, common cathode", 8)
    pitch = 2.54
    # signal pads: 1.6 wide x 2.0 tall, centers y=+/-4.3 (wrap-around toe)
    for i in range(6):  # pins 1-6 bottom L->R
        x = -6.35 + i * pitch
        s += pad_smd(i + 1, round(x, 2), 4.3, 2.0, 2.2)
    for i in range(6):  # pins 7-12 top R->L
        x = 6.35 - i * pitch
        s += pad_smd(7 + i, round(x, 2), -4.3, 2.0, 2.2)
    # anchor pads (mechanical, unnumbered -> not in netlist)
    for x in (-11.43, 11.43):
        for y in (-4.3, 4.3):
            s += pad_smd("", x, y, 2.0, 2.0)
    # body outline
    s += rect(-14.25, -5.0, 14.25, 5.0, "F.Fab")
    for yy in (-5.0, 5.0):
        s += line(-14.25, yy, -12.8, yy, "F.SilkS", 0.15)
        s += line(12.8, yy, 14.25, yy, "F.SilkS", 0.15)
    s += line(-14.25, -5.0, -14.25, 5.0, "F.SilkS", 0.15)
    s += line(14.25, -5.0, 14.25, 5.0, "F.SilkS", 0.15)
    # pin 1 marker (bottom-left signal pad)
    s += circle(-8.3, 5.0, 0.15, "F.SilkS", 0.3, "yes")
    s += text_fab("28.5x10 4-DIG", 0, 0)
    s += rect(-14.4, -5.6, 14.4, 5.6, "F.CrtYd", 0.05)
    s += MODEL.format(path="${KIPRJMOD}/../mech/xl_sa2401.step")
    s += ")\n"
    return "XL-SA2401SRWC", s


def battery():
    s = HDR.format(name="BS-08-B2AA001", attr="smd")
    s += prop("Reference", "REF**", -9.2, hide=False, layer="F.SilkS")
    s += prop("Value", "BS-08-B2AA001", 9.2)
    s += prop("Footprint", "", 11)
    s += prop("Datasheet", "", 11)
    s += prop("Description", "CR2032 SMD holder MYOUNG BS-08", 11)
    # pad 1 = + (right, 3.5x3.8, right edge +14.75); pad 2 = - (left, 4.3x2.8,
    # left edge -10.95)
    s += pad_smd(1, 13.0, 0, 3.5, 3.8)
    s += pad_smd(2, -8.8, 0, 4.3, 2.8)
    # body: 24.1 x 15.7 centered on cavity center
    s += rect(-12.05, -7.85, 12.05, 7.85, "F.Fab")
    s += circle(0, 0, 10.15, "F.Fab")  # cavity
    # silk: top/bottom edges only (leave left open = insertion mouth)
    for yy in (-7.85, 7.85):
        s += line(-12.05, yy, 12.05, yy, "F.SilkS", 0.15)
    s += line(12.05, -7.85, 12.05, -2.6, "F.SilkS", 0.15)
    s += line(12.05, 2.6, 12.05, 7.85, "F.SilkS", 0.15)
    s += (f'\t(fp_text user "+" (at 13.0 -3.6 0) (layer "F.SilkS") '
          f'(effects (font (size 1.2 1.2) (thickness 0.2))))\n')
    s += text_fab("CR2032", -8.0, 0, 0.8)
    s += rect(-12.35, -8.15, 12.35, 8.15, "F.CrtYd", 0.05)  # body
    s += rect(12.15, -2.4, 15.35, 2.4, "F.CrtYd", 0.05)      # (+) tab zone
    s += MODEL.format(path="${KIPRJMOD}/../mech/bs08_holder.step")
    s += ")\n"
    return "BS-08-B2AA001", s


def switch():
    s = HDR.format(name="SW_TS-1187A", attr="smd")
    s += prop("Reference", "REF**", -3.9, hide=False, layer="F.SilkS")
    s += prop("Value", "TS-1187A-B-A-B", 3.9)
    s += prop("Footprint", "", 5)
    s += prop("Datasheet", "", 5)
    s += prop("Description", "Tactile switch SMD 5.1x5.1x1.5 XKB", 5)
    # 1=A top-left, 2=B top-right, 3=C bottom-left, 4=D bottom-right
    s += pad_smd(1, -3.1, -1.875, 1.2, 0.9)
    s += pad_smd(2, 3.1, -1.875, 1.2, 0.9)
    s += pad_smd(3, -3.1, 1.875, 1.2, 0.9)
    s += pad_smd(4, 3.1, 1.875, 1.2, 0.9)
    s += rect(-2.55, -2.55, 2.55, 2.55, "F.Fab")
    s += circle(0, 0, 1.0, "F.Fab")
    for xx in (-2.55, 2.55):
        s += line(xx, -0.8, xx, 0.8, "F.SilkS", 0.15)
    for yy in (-2.55, 2.55):
        s += line(-2.0, yy, 2.0, yy, "F.SilkS", 0.15)
    s += rect(-3.95, -2.85, 3.95, 2.85, "F.CrtYd", 0.05)
    s += MODEL.format(path="${KIPRJMOD}/../mech/ts1187a.step")
    s += ")\n"
    return "SW_TS-1187A", s


def keyring_hole():
    s = HDR.format(name="KeyringHole_4mm",
                   attr="exclude_from_pos_files exclude_from_bom")
    # plated + grounded: the split ring wears on ENIG copper, not laminate
    s += prop("Reference", "REF**", -4.5, hide=True, layer="F.SilkS")
    s += prop("Value", "KeyringHole", 4.5)
    s += prop("Footprint", "", 6)
    s += prop("Datasheet", "", 6)
    s += prop("Description", "4mm NPTH keyring hole", 6)
    s += ('\t(pad "1" thru_hole circle (at 0 0) (size 6.6 6.6) '
          '(drill 4.0) (layers "*.Cu" "*.Mask"))\n')
    s += circle(0, 0, 2.8, "F.CrtYd", 0.05)
    s += ")\n"
    return "KeyringHole_4mm", s


def main():
    os.makedirs(OUT, exist_ok=True)
    for gen in (display, battery, switch, keyring_hole):
        name, content = gen()
        path = os.path.join(OUT, name + ".kicad_mod")
        with open(path, "w") as f:
            f.write(content)
        print("wrote", path)


if __name__ == "__main__":
    main()
