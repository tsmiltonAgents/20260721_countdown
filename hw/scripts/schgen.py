"""Programmatic KiCad schematic generator.

Strategy: symbols are placed on a grid; every pin that carries a net gets a
global label placed exactly at the pin's connection point (KiCad connects a
label that sits on a pin end without needing a wire). Power is a net like any
other, with PWR_FLAG symbols to satisfy ERC. Connectivity is then verified by
exporting the netlist with kicad-cli and diffing against the intended netlist
— so correctness never depends on drawing geometry being pretty.
"""
import uuid as uuidlib

from sexp import Sym, parse, dump, find, find_all

S = Sym
FMT_VERSION = 20250114


def new_uuid():
    return str(uuidlib.uuid4())


def load_symbol(lib_path, name):
    """Extract a symbol definition (and its pins) from a .kicad_sym library."""
    with open(lib_path) as f:
        lib = parse(f.read())
    for sym in find_all(lib, "symbol"):
        if sym[1] == name:
            return sym
    raise KeyError(f"{name} not in {lib_path}")


def symbol_pins(sym, unit=1):
    """Return [(number, name, x, y)] connection points for a symbol, given
    the symbol s-expr as stored in a library (with nested unit sub-symbols).
    Includes unit-0 (common) and the requested unit's pins."""
    pins = []
    base = sym[1].split(":")[-1]
    for sub in find_all(sym, "symbol"):
        subname = sub[1]
        # sub-symbol names end with _<unit>_<style>
        parts = subname.rsplit("_", 2)
        if len(parts) < 3:
            continue
        u = int(parts[1])
        if u not in (0, unit):
            continue
        for pin in find_all(sub, "pin"):
            at = find(pin, "at")
            num = find(pin, "number")[1]
            nam = find(pin, "name")[1]
            ang = float(at[3]) if len(at) > 3 else 0
            pins.append((str(num), str(nam), float(at[1]), float(at[2]), ang))
    # resolve "extends" (derived symbols) not handled here on purpose
    return pins


class Schematic:
    def __init__(self, project_name, title):
        self.project = project_name
        self.title = title
        self.root_uuid = new_uuid()
        self.lib_symbols = {}   # lib_id -> symbol def (renamed)
        self.symbol_pins = {}   # lib_id -> pins list
        self.instances = []     # s-expr symbol instances
        self.labels = []        # global labels
        self.texts = []
        self.netmap = {}        # ref -> {pin: net}

    def add_lib_symbol(self, lib_id, sym_def):
        if lib_id in self.lib_symbols:
            return
        sym = [x for x in sym_def]  # shallow copy
        old_base = str(sym_def[1]).split(":")[-1]
        new_base = lib_id.split(":")[-1]
        sym[1] = lib_id
        # sub-symbol (unit) names must match the parent symbol name
        for i, child in enumerate(sym):
            if isinstance(child, list) and child and child[0] == "symbol":
                child = [x for x in child]
                child[1] = new_base + str(child[1])[len(old_base):]
                sym[i] = child
        self.lib_symbols[lib_id] = sym
        self.symbol_pins[lib_id] = symbol_pins(sym_def)

    def place(self, lib_id, ref, value, at, nets, footprint="", lcsc="",
              rotation=0, extra_fields=(), dnp=False):
        """Place a symbol instance. nets: {pin_number: net_name}. Every pin
        gets a label; pins absent from nets get a no-connect flag."""
        X = round(round(at[0] / 1.27) * 1.27, 4)
        Y = round(round(at[1] / 1.27) * 1.27, 4)
        pins = self.symbol_pins[lib_id]
        pin_names = {n for n, *_ in pins}
        for p in nets:
            if p not in pin_names:
                raise ValueError(f"{ref}: net given for nonexistent pin {p}; has {sorted(pin_names)}")
        inst_uuid = new_uuid()
        inst = [S("symbol"),
                [S("lib_id"), lib_id],
                [S("at"), X, Y, rotation],
                [S("unit"), 1],
                [S("exclude_from_sim"), S("no")],
                [S("in_bom"), S("no") if dnp else S("yes")],
                [S("on_board"), S("yes")],
                [S("dnp"), S("yes") if dnp else S("no")],
                [S("uuid"), inst_uuid]]
        props = [("Reference", ref, X, Y - 3.81, False),
                 ("Value", value, X, Y + 3.81, False),
                 ("Footprint", footprint, X, Y + 6.35, True),
                 ("Datasheet", "", X, Y, True),
                 ("Description", "", X, Y, True)]
        if lcsc:
            props.append(("LCSC", lcsc, X, Y + 8.89, True))
        for name, val, px, py, hide in list(props) + list(extra_fields):
            prop = [S("property"), name, val,
                    [S("at"), px, py, 0],
                    [S("effects"),
                     [S("font"), [S("size"), 1.27, 1.27]],
                     ([S("hide"), S("yes")] if hide else [S("justify"), S("left")])]]
            inst.append(prop)
        for num, *_ in pins:
            inst.append([S("pin"), num, [S("uuid"), new_uuid()]])
        inst.append([S("instances"),
                     [S("project"), self.project,
                      [S("path"), "/" + self.root_uuid,
                       [S("reference"), ref], [S("unit"), 1]]]])
        self.instances.append(inst)
        self.netmap[ref] = dict(nets)

        # labels / no-connects at absolute pin positions
        for num, name, px, py, pang in pins:
            ax, ay = _pin_abs(X, Y, px, py, rotation)
            if num in nets:
                lang = int((pang + 180 + rotation) % 360)
                self.labels.append(_global_label(nets[num], ax, ay, lang))
            else:
                self.labels.append([S("no_connect"), [S("at"), ax, ay],
                                    [S("uuid"), new_uuid()]])
        return inst_uuid

    def add_text(self, txt, x, y, size=2.0):
        self.texts.append([S("text"), txt, [S("exclude_from_sim"), S("no")],
                           [S("at"), x, y, 0],
                           [S("effects"), [S("font"), [S("size"), size, size]],
                            [S("justify"), S("left")]],
                           [S("uuid"), new_uuid()]])

    def emit(self):
        doc = [S("kicad_sch"),
               [S("version"), FMT_VERSION],
               [S("generator"), "schgen"],
               [S("generator_version"), "10.0"],
               [S("uuid"), self.root_uuid],
               [S("paper"), "A3"],
               [S("title_block"), [S("title"), self.title],
                [S("date"), "2026-07-21"], [S("rev"), "A"]]]
        libsec = [S("lib_symbols")] + list(self.lib_symbols.values())
        doc.append(libsec)
        doc.extend(self.labels)
        doc.extend(self.texts)
        doc.extend(self.instances)
        doc.append([S("sheet_instances"),
                    [S("path"), "/", [S("page"), "1"]]])
        doc.append([S("embedded_fonts"), S("no")])
        return dump(doc) + "\n"

    def intended_nets(self):
        """net -> set of (ref, pin) — ground truth for verification."""
        nets = {}
        for ref, pinmap in self.netmap.items():
            for pin, net in pinmap.items():
                nets.setdefault(net, set()).add((ref, pin))
        return nets


def _pin_abs(X, Y, px, py, rotation):
    """Absolute canvas position of a symbol pin. Canvas Y grows downward;
    symbol-space Y grows upward. Rotation is CCW in symbol space."""
    if rotation == 0:
        dx, dy = px, -py
    elif rotation == 90:
        dx, dy = -py, -px
    elif rotation == 180:
        dx, dy = -px, py
    elif rotation == 270:
        dx, dy = py, px
    else:
        raise ValueError(rotation)
    return round(X + dx, 4), round(Y + dy, 4)


def _global_label(net, x, y, angle=0):
    just = {0: "left", 90: "left", 180: "right", 270: "right"}[angle % 360]
    return [S("global_label"), net,
            [S("shape"), S("passive")],
            [S("at"), x, y, angle % 360],
            [S("effects"), [S("font"), [S("size"), 1.27, 1.27]],
             [S("justify"), S(just)]],
            [S("uuid"), new_uuid()]]


def make_symbol(name, pins, ref_prefix="U", width=10.16):
    """Author a custom single-unit symbol.
    pins: list of (number, name, etype, side, slot) where side in 'L','R'
    and slot is the 0-based vertical slot index. etype: input/output/bidirectional/
    passive/power_in/power_out/open_collector etc (KiCad electrical types)."""
    half = width / 2
    nslots = max(s for *_, s in pins) + 1
    height = (nslots + 1) * 2.54
    top = height / 2
    body = [S("symbol"), f"{name}_0_1",
            [S("rectangle"),
             [S("start"), -half, top],
             [S("end"), half, top - height],
             [S("stroke"), [S("width"), 0.254], [S("type"), S("solid")]],
             [S("fill"), [S("type"), S("background")]]]]
    unit = [S("symbol"), f"{name}_1_1"]
    for num, pname, etype, side, slot in pins:
        y = top - (slot + 1) * 2.54
        if side == "L":
            x, ang = -half - 2.54, 0
        else:
            x, ang = half + 2.54, 180
        unit.append([S("pin"), S(etype), S("line"),
                     [S("at"), x, y, ang],
                     [S("length"), 2.54],
                     [S("name"), pname, [S("effects"), [S("font"), [S("size"), 1.27, 1.27]]]],
                     [S("number"), str(num), [S("effects"), [S("font"), [S("size"), 1.27, 1.27]]]]])
    sym = [S("symbol"), name,
           [S("exclude_from_sim"), S("no")],
           [S("in_bom"), S("yes")],
           [S("on_board"), S("yes")],
           [S("property"), "Reference", ref_prefix, [S("at"), 0, top + 2.54, 0],
            [S("effects"), [S("font"), [S("size"), 1.27, 1.27]]]],
           [S("property"), "Value", name, [S("at"), 0, -top - 2.54, 0],
            [S("effects"), [S("font"), [S("size"), 1.27, 1.27]]]],
           body, unit]
    return sym
