#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


def parse_cnf(path: Path):
    comments = []
    clauses = []
    num_vars = None

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()

            if not s:
                continue

            if s.startswith("c"):
                comments.append(line.rstrip("\n"))
                continue

            if s.startswith("p cnf"):
                parts = s.split()
                num_vars = int(parts[2])
                continue

            clauses.append(s)

    if num_vars is None:
        raise ValueError(f"CNF header not found: {path}")

    return comments, num_vars, clauses


def parse_inputs(map_path: Path):
    inputs = {}
    in_re = re.compile(r"input\s+(\d+)\s+aig_lit\s+-?\d+\s+dimacs_lit\s+(-?\d+)")

    for line in map_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = in_re.search(line)
        if m:
            inputs[int(m.group(1))] = int(m.group(2))

    return inputs


def word_bits(value: int):
    return [(value >> (15 - j)) & 1 for j in range(16)]


def key_bits(words):
    bits = []
    for w in words:
        bits.extend(word_bits(w))
    return bits


def unit(lit: int, bit: int):
    return lit if bit else -lit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cnf", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--out", required=True)

    ap.add_argument("--k0", required=True)
    ap.add_argument("--k1", required=True)
    ap.add_argument("--k2", required=True)
    ap.add_argument("--k3", required=True)

    args = ap.parse_args()

    comments, num_vars, clauses = parse_cnf(Path(args.cnf))
    inputs = parse_inputs(Path(args.map))

    words = [
        int(args.k0, 16),
        int(args.k1, 16),
        int(args.k2, 16),
        int(args.k3, 16),
    ]

    bits = key_bits(words)

    units = []
    for i, bit in enumerate(bits):
        if i not in inputs:
            raise KeyError(f"key input {i} not found in map")

        lit = inputs[i]
        units.append(f"{unit(lit, bit)} 0")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        for c in comments:
            f.write(c + "\n")

        f.write("c fixed key for reverse_round check\n")
        f.write(f"p cnf {num_vars} {len(clauses) + len(units)}\n")

        for cl in clauses:
            f.write(cl + "\n")

        for u in units:
            f.write(u + "\n")

    print("OK")
    print(f"added key units: {len(units)}")
    print(f"out: {out}")


if __name__ == "__main__":
    main()
