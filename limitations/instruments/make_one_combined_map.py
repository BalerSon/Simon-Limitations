#!/usr/bin/env python3
from pathlib import Path
import argparse

def read_full_map(path):
    inputs = {}
    outputs = {}

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) != 6:
            continue

        kind = parts[0]
        idx = int(parts[1])
        aig_lit = int(parts[3])
        dimacs_lit = int(parts[5])

        if kind == "input":
            inputs[idx] = (aig_lit, dimacs_lit)
        elif kind == "output":
            outputs[idx] = (aig_lit, dimacs_lit)

    return inputs, outputs

def input_name(index, blocks):
    if index < 64:
        w = index // 16
        bit = index % 16
        return f"key[{w}][{bit}]"

    x = index - 64
    b = x // 32
    rem = x % 32
    w = rem // 16
    bit = rem % 16
    return f"pt[{b}][{w}][{bit}]"

def output_name(index, rounds, blocks):
    ct_bits = blocks * 32

    if index < ct_bits:
        b = index // 32
        rem = index % 32
        w = rem // 16
        bit = rem % 16
        return f"ct[{b}][{w}][{bit}]"

    x = index - ct_bits
    r = x // 16
    bit = x % 16
    return f"rk[{r}][{bit}]"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, required=True)
    ap.add_argument("--blocks", type=int, required=True)
    ap.add_argument("--full-map", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    inputs, outputs = read_full_map(Path(args.full_map))

    expected_inputs = 64 + args.blocks * 32
    expected_outputs = args.blocks * 32 + args.rounds * 16

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w") as f:
        f.write("# Combined map\n")
        f.write(f"# rounds={args.rounds}, blocks={args.blocks}\n")
        f.write("# Format:\n")
        f.write("# <name> input/output <index> aig_lit <aig_lit> dimacs_lit <dimacs_lit>\n\n")

        f.write("# Inputs\n")
        for i in range(expected_inputs):
            aig_lit, dimacs_lit = inputs[i]
            f.write(f"{input_name(i, args.blocks)} input {i} aig_lit {aig_lit} dimacs_lit {dimacs_lit}\n")

        f.write("\n# Outputs\n")
        for i in range(expected_outputs):
            aig_lit, dimacs_lit = outputs[i]
            f.write(f"{output_name(i, args.rounds, args.blocks)} output {i} aig_lit {aig_lit} dimacs_lit {dimacs_lit}\n")

    print(f"written {out}")

if __name__ == "__main__":
    main()
