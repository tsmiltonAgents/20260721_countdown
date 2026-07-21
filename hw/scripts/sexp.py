"""Minimal KiCad s-expression parser/serializer."""


class Sym(str):
    """Bare symbol (unquoted token)."""
    __slots__ = ()


def parse(text):
    """Parse s-expression text into nested lists of Sym/str/int/float."""
    tokens = _tokenize(text)
    pos = [0]

    def read():
        tok = tokens[pos[0]]
        pos[0] += 1
        if tok == "(":
            out = []
            while tokens[pos[0]] != ")":
                out.append(read())
            pos[0] += 1
            return out
        if tok == ")":
            raise ValueError("unexpected )")
        if isinstance(tok, tuple):  # quoted string
            return tok[0]
        # bare token: try number
        try:
            return int(tok)
        except ValueError:
            try:
                return float(tok)
            except ValueError:
                return Sym(tok)

    result = read()
    return result


def _tokenize(text):
    toks = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c in "()":
            toks.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while text[j] != '"':
                if text[j] == "\\":
                    buf.append(text[j + 1])
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            toks.append(("".join(buf),))  # tuple marks quoted string
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()"':
                j += 1
            toks.append(text[i:j])
            i = j
    return toks


def dump(node, indent=0):
    """Serialize back to KiCad-style s-expression text."""
    if isinstance(node, list):
        pad = "\t" * indent
        # short lists with no sublists on one line
        if not any(isinstance(x, list) for x in node):
            return pad + "(" + " ".join(_atom(x) for x in node) + ")"
        parts = [pad + "(" + _atom(node[0])]
        head_atoms = []
        idx = 1
        while idx < len(node) and not isinstance(node[idx], list):
            head_atoms.append(_atom(node[idx]))
            idx += 1
        if head_atoms:
            parts[0] += " " + " ".join(head_atoms)
        for child in node[idx:]:
            parts.append(dump(child, indent + 1))
        parts.append("\t" * indent + ")")
        return "\n".join(parts)
    return "\t" * indent + _atom(node)


def _atom(x):
    if isinstance(x, list):
        raise ValueError("nested list in atom position")
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        s = f"{x:.6f}".rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    # string -> quoted
    s = str(x).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def find(node, name):
    """First child list whose head == name."""
    for child in node:
        if isinstance(child, list) and child and child[0] == name:
            return child
    return None


def find_all(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]
