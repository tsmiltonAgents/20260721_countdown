"""Diff a kicad netlist export against the generator's intended netlist.

Usage: python3 verify_netlist.py <exported.net> <intended.json>
intended.json: {"NETNAME": [["R1","1"], ...], ...}
Refs beginning with # (power symbols/flags) are ignored on both sides.
Exit 0 only on an exact match.
"""
import json
import sys

from sexp import parse, find, find_all


def exported_nets(path):
    net = parse(open(path).read())
    out = {}
    for n in find_all(find(net, "nets"), "net"):
        name = str(find(n, "name")[1])
        nodes = {(str(find(nd, "ref")[1]), str(find(nd, "pin")[1]))
                 for nd in find_all(n, "node")
                 if not str(find(nd, "ref")[1]).startswith("#")}
        if name.startswith("unconnected-") and len(nodes) == 1:
            continue  # intentional no-connect pin
        if nodes:
            out[name] = nodes
    return out


def main():
    got = exported_nets(sys.argv[1])
    want = {k: {tuple(x) for x in v} for k, v in json.load(open(sys.argv[2])).items()}
    want = {k: {(r, p) for r, p in v if not r.startswith("#")} for k, v in want.items()}
    want = {k: v for k, v in want.items() if v}
    ok = True
    for name in sorted(set(got) | set(want)):
        g, w = got.get(name, set()), want.get(name, set())
        if g != w:
            ok = False
            print(f"MISMATCH net {name}:")
            for extra in sorted(g - w):
                print(f"  exported has extra node {extra}")
            for missing in sorted(w - g):
                print(f"  exported missing node {missing}")
    if ok:
        n_nodes = sum(len(v) for v in want.values())
        print(f"NETLIST OK: {len(want)} nets, {n_nodes} nodes match intent exactly")
    sys.exit(0 if ok else 1)


main()
