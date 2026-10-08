"""Minimal S-expression reader/writer for KiCad files (.kicad_sym, .kicad_sch)."""
import re

_TOKEN = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Sym(str):
    """An unquoted atom (keyword or number), as opposed to a quoted string."""


def parse(text):
    stack, cur, pos = [], [], 0
    while True:
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        lp, rp, s, a = m.groups()
        if lp:
            stack.append(cur)
            cur = []
        elif rp:
            done, cur = cur, stack.pop()
            cur.append(done)
        elif s is not None:
            cur.append(s[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            cur.append(Sym(a))
    return cur[0] if len(cur) == 1 else cur


def dump(node, indent=0):
    pad = '\t' * indent
    if not isinstance(node, list):
        if isinstance(node, Sym):
            return node
        if isinstance(node, (int, float)):
            return fmt_num(node)
        return '"' + str(node).replace('\\', '\\\\').replace('"', '\\"') + '"'
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return '(' + ' '.join(dump(c) for c in node) + ')'
    out = '(' + ' '.join(dump(c) for c in node if not isinstance(c, list))
    for c in node:
        if isinstance(c, list):
            out += '\n' + pad + '\t' + dump(c, indent + 1)
    return out + '\n' + pad + ')'


def fmt_num(v):
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key):
    r = find(node, key)
    return r[0] if r else None
