"""DSN surgery for two-stage freerouting.

stage1: keep only the given nets in (network ...) so freerouting routes just
        those (all pads remain as obstacles).
protect: tag every (wire ...) / (via ...) in (wiring ...) with (type protect)
        so a later freerouting pass cannot rip stage-1 routes.

Usage:
  python3 dsn_stage.py stage1 in.dsn out.dsn NET1,NET2,...
  python3 dsn_stage.py protect in.dsn out.dsn
"""
import re
import sys


def stage1(text, keep):
    def net_repl(m):
        name = m.group(1).strip('"')
        return m.group(0) if name in keep else ""
    # (net NAME (pins ...)) blocks: pins list has no nested parens
    text = re.sub(r'\(net ("[^"]+"|\S+)\s*\(pins[^()]*\)\s*\)\s*', net_repl, text)

    # class blocks list net names as bare/quoted tokens before (circuit/rule
    def class_repl(m):
        head, body = m.group(1), m.group(2)
        toks = []
        for tok in re.findall(r'"[^"]+"|\S+', body):
            name = tok.strip('"')
            if name in keep or tok.startswith("("):
                toks.append(tok)
        return head + " " + " ".join(toks) + "\n      (circuit"
    text = re.sub(r'(\(class\s+\S+)((?:\s+(?:"[^"]+"|[^\s()]+))*)\s*\(circuit',
                  class_repl, text)
    return text


def emptynets(text, names):
    def repl(m):
        name = m.group(1).strip('"')
        if name in names:
            return "(net " + m.group(1) + " (pins)\n    )\n    "
        return m.group(0)
    return re.sub(r'\(net ("[^"]+"|\S+)\s*\(pins[^()]*\)\s*\)\s*', repl, text)


def protect(text):
    # wires: pcbnew exports (wire (path ...) (net X) (type route)?) — normalize
    if "(type route)" in text:
        text = text.replace("(type route)", "(type protect)")
    # add protect to wires lacking a type, and to vias in wiring section
    def wire_repl(m):
        block = m.group(0)
        if "(type" in block:
            return block
        return block[:-1] + "(type protect))"
    text = re.sub(r'\(wire\s*\(path[^()]*\)\s*(?:\(net (?:"[^"]+"|\S+)\)\s*)?\)',
                  wire_repl, text)
    def via_repl(m):
        block = m.group(0)
        if "(type" in block:
            return block
        return block[:-1] + "(type protect))"
    text = re.sub(r'\(via\s+(?:"[^"]+"|\S+)[^()]*(?:\(net (?:"[^"]+"|\S+)\)\s*)?\)',
                  via_repl, text)
    return text


def inset(text, margin_um10):
    """Clamp the boundary polygon inward so freerouting keeps copper off the
    real board edge. Coordinates are um*10; y is negative downward."""
    m = re.search(r'(\(boundary\s*\(path pcb \d+)([\s\-\d.]+)(\)\s*\))', text)
    if not m:
        raise SystemExit("boundary not found")
    import math
    nums = [float(v) for v in m.group(2).split()]
    xs = nums[0::2]
    ys = nums[1::2]
    x0, x1 = min(xs) + margin_um10, max(xs) - margin_um10
    y0, y1 = min(ys) + margin_um10, max(ys) - margin_um10
    r = 26000.0  # 2.6 mm corner radius after inset
    corners = [  # (cx, cy, start_angle) counter-clockwise in DSN space
        (x1 - r, y1 - r, 0.0),
        (x0 + r, y1 - r, 90.0),
        (x0 + r, y0 + r, 180.0),
        (x1 - r, y0 + r, 270.0),
    ]
    pts = []
    for cx, cy, a0 in corners:
        for k in range(13):
            a = math.radians(a0 + 90.0 * k / 12)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append(pts[0])
    out = [f"{x:.0f} {y:.0f}" for x, y in pts]
    return text[:m.start(2)] + "\n      " + "\n      ".join(out) + "\n    " + text[m.end(2):]


def ses_dropnets(text, names):
    """Remove whole (net NAME ...) blocks (balanced) from a SES file so the
    importer leaves those nets' board wiring untouched."""
    out = []
    i = 0
    while i < len(text):
        m = re.search(r'\(net ("[^"]+"|\S+)', text[i:])
        if not m:
            out.append(text[i:])
            break
        start = i + m.start()
        name = m.group(1).strip('"')
        out.append(text[i:start])
        # scan balanced parens from 'start'
        depth = 0
        j = start
        while j < len(text):
            if text[j] == '(':
                depth += 1
            elif text[j] == ')':
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        block = text[start:j]
        if name not in names:
            out.append(block)
        i = j
    return "".join(out)


def main():
    mode, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    text = open(src).read()
    if mode == "stage1":
        keep = set(sys.argv[4].split(","))
        text = stage1(text, keep)
    elif mode == "protect":
        text = protect(text)
    elif mode == "emptynets":
        text = emptynets(text, set(sys.argv[4].split(",")))
    elif mode == "inset":
        text = inset(text, float(sys.argv[4]))
    elif mode == "ses_dropnets":
        text = ses_dropnets(text, set(sys.argv[4].split(",")))
    else:
        raise SystemExit("unknown mode")
    open(dst, "w").write(text)
    print(f"{mode}: wrote {dst}")


main()
