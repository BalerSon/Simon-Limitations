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


def parse_map(path: Path):
    inputs = {}
    outputs = {}

    in_re = re.compile(r"input\s+(\d+)\s+aig_lit\s+-?\d+\s+dimacs_lit\s+(-?\d+)")
    out_re = re.compile(r"output\s+(\d+)\s+aig_lit\s+-?\d+\s+dimacs_lit\s+(-?\d+)")

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = in_re.search(line)
        if m:
            inputs[int(m.group(1))] = int(m.group(2))
            continue

        m = out_re.search(line)
        if m:
            outputs[int(m.group(1))] = int(m.group(2))
            continue

    return inputs, outputs


def word_bits(value: int):
    return [(value >> (15 - j)) & 1 for j in range(16)]


def two_words_bits(w0: int, w1: int):
    return word_bits(w0) + word_bits(w1)


def unit(lit: int, bit: int):
    return lit if bit else -lit


def add_units(units, mapping, start, bits, label):
    for offset, bit in enumerate(bits):
        idx = start + offset

        if idx not in mapping:
            raise KeyError(f"{label}: index {idx} not found in map")

        units.append(f"{unit(mapping[idx], bit)} 0")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cnf", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rounds", type=int, required=True)

    ap.add_argument("--pt0", required=True)
    ap.add_argument("--pt1", required=True)
    ap.add_argument("--ct0", required=True)
    ap.add_argument("--ct1", required=True)

    args = ap.parse_args()

    comments, num_vars, clauses = parse_cnf(Path(args.cnf))
    inputs, outputs = parse_map(Path(args.map))

    pt_bits = two_words_bits(int(args.pt0, 16), int(args.pt1, 16))
    ct_bits = two_words_bits(int(args.ct0, 16), int(args.ct1, 16))

    units = []

    # input:
    # 0..63    key
    # 64..95   plaintext
    # 96..127  known ciphertext
    add_units(units, inputs, 64, pt_bits, "input plaintext")
    add_units(units, inputs, 96, ct_bits, "input known ciphertext")

    # output:
    # 0..31                   computed ciphertext
    # 32..32+rounds*16-1      round keys
    # 32+rounds*16..+31       reverse plaintext
    reverse_pt_start = 32 + args.rounds * 16

    add_units(units, outputs, 0, ct_bits, "output computed ciphertext")
    add_units(units, outputs, reverse_pt_start, pt_bits, "output reverse plaintext")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        for c in comments:
            f.write(c + "\n")

        f.write("c reverse_round instance\n")
        f.write(f"c rounds={args.rounds}\n")
        f.write("c fixed plaintext input, known ciphertext input, computed ciphertext output, reverse plaintext output\n")
        f.write(f"p cnf {num_vars} {len(clauses) + len(units)}\n")

        for cl in clauses:
            f.write(cl + "\n")

        for u in units:
            f.write(u + "\n")

    print("OK")
    print(f"vars: {num_vars}")
    print(f"old clauses: {len(clauses)}")
    print(f"added units: {len(units)}")
    print(f"new clauses: {len(clauses) + len(units)}")
    print(f"out: {out}")


if __name__ == "__main__":
    main()
