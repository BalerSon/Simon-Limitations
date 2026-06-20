#!/usr/bin/env python3
from pathlib import Path
import re
import argparse

ROUNDS_LIST = [10, 11, 12, 13, 14]
KEYS_LIST = [1, 2, 3, 4, 5]
BLOCKS_LIST = [1, 2, 4, 8]


def parse_experimental_data(path):
    data = {}
    current_rounds = None
    current_key_id = None
    current_key_value = None
    current_blocks = None

    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line:
            continue

        m = re.match(r"Rounds:\s*(\d+)", line)
        if m:
            current_rounds = int(m.group(1))
            data.setdefault(current_rounds, {})
            continue

        m = re.match(r"Key_(\d+):\s*0x([0-9A-Fa-f]+)", line)
        if m:
            current_key_id = int(m.group(1))
            current_key_value = int(m.group(2), 16)
            data[current_rounds].setdefault(current_key_id, {})
            continue

        m = re.match(r"Blocks:\s*(\d+)", line)
        if m:
            current_blocks = int(m.group(1))
            data[current_rounds][current_key_id][current_blocks] = {
                "key": current_key_value,
                "P": [],
                "C": [],
            }
            continue

        m = re.match(r"P_(\d+):\s*0x([0-9A-Fa-f]+)", line)
        if m:
            idx = int(m.group(1))
            val = int(m.group(2), 16)
            arr = data[current_rounds][current_key_id][current_blocks]["P"]
            while len(arr) < idx:
                arr.append(None)
            arr[idx - 1] = val
            continue

        m = re.match(r"C_(\d+):\s*0x([0-9A-Fa-f]+)", line)
        if m:
            idx = int(m.group(1))
            val = int(m.group(2), 16)
            arr = data[current_rounds][current_key_id][current_blocks]["C"]
            while len(arr) < idx:
                arr.append(None)
            arr[idx - 1] = val
            continue

    return data


def parse_reverse_map(path):
    inputs = {}
    outputs = {}

    in_re = re.compile(r"input\s+(\d+)\s+aig_lit\s+-?\d+\s+dimacs_lit\s+(-?\d+)")
    out_re = re.compile(r"output\s+(\d+)\s+aig_lit\s+-?\d+\s+dimacs_lit\s+(-?\d+)")

    for raw in Path(path).read_text().splitlines():
        line = raw.strip()

        m = in_re.match(line)
        if m:
            inputs[int(m.group(1))] = int(m.group(2))
            continue

        m = out_re.match(line)
        if m:
            outputs[int(m.group(1))] = int(m.group(2))
            continue

    return inputs, outputs


def split32_hi_lo(x):
    return [(x >> 16) & 0xFFFF, x & 0xFFFF]


def bit_msb(word, bit):
    return (word >> (15 - bit)) & 1


def unit(lit, value):
    return lit if value else -lit


def add_units_for_32(units, mapping, start_index, value32, label):
    words = split32_hi_lo(value32)

    offset = 0
    for w in range(2):
        for bit in range(16):
            idx = start_index + offset
            if idx not in mapping:
                raise KeyError(f"{label}: index {idx} not found in map")

            val = bit_msb(words[w], bit)
            units.append(unit(mapping[idx], val))
            offset += 1


def build_reverse_units(inputs, outputs, rounds, blocks, plaintexts, ciphertexts):
    units = []

    # Input layout:
    # 0..63                         key
    # 64..64+blocks*32-1            plaintexts
    # 64+blocks*32..+blocks*32-1    known ciphertexts

    pt_input_start = 64
    known_ct_input_start = 64 + blocks * 32

    # Output layout:
    # 0..blocks*32-1                      computed ciphertexts
    # blocks*32..blocks*32+rounds*16-1    round keys
    # blocks*32+rounds*16..               reverse plaintexts

    computed_ct_output_start = 0
    reverse_pt_output_start = blocks * 32 + rounds * 16

    for b in range(blocks):
        p = plaintexts[b]
        c = ciphertexts[b]

        add_units_for_32(
            units,
            inputs,
            pt_input_start + b * 32,
            p,
            f"input plaintext block {b}",
        )

        add_units_for_32(
            units,
            inputs,
            known_ct_input_start + b * 32,
            c,
            f"input known ciphertext block {b}",
        )

        add_units_for_32(
            units,
            outputs,
            computed_ct_output_start + b * 32,
            c,
            f"output computed ciphertext block {b}",
        )

        add_units_for_32(
            units,
            outputs,
            reverse_pt_output_start + b * 32,
            p,
            f"output reverse plaintext block {b}",
        )

    return units


def read_cnf(path):
    lines = Path(path).read_text().splitlines()

    for i, line in enumerate(lines):
        if line.startswith("p cnf"):
            parts = line.split()
            return lines, i, int(parts[2]), int(parts[3])

    raise ValueError(f"No p cnf header in {path}")


def write_instance(src, dst, units):
    lines, header_idx, nvars, nclauses = read_cnf(src)

    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    with dst.open("w") as f:
        for i, line in enumerate(lines):
            if i == header_idx:
                f.write(f"p cnf {nvars} {nclauses + len(units)}\n")
            else:
                f.write(line + "\n")

        for lit in units:
            f.write(f"{lit} 0\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--base",
        default="/home/balerso/Simon/Simon-Limitations/limitations/LIMITEDCNF/reverse_round",
    )
    ap.add_argument(
        "--data",
        default="/home/balerso/Simon/Simon-Limitations/limitations/instruments/data_gen/experimental_data.txt",
    )
    args = ap.parse_args()

    base = Path(args.base)
    data = parse_experimental_data(args.data)

    total = 0

    for r in ROUNDS_LIST:
        for k in KEYS_LIST:
            for b in BLOCKS_LIST:
                entry = data[r][k][b]

                shared = base / f"{r}roundsCNF" / "shared"

                cnf = shared / "cnfs" / f"simon32_64_r{r}_b{b}_reverse_rk_opt_mapped.cnf"
                cmap = shared / "maps" / f"simon32_64_r{r}_b{b}_reverse_rk_combined_map.txt"

                out = (
                    base
                    / f"{r}roundsCNF"
                    / f"K{k}"
                    / "instances"
                    / f"simon32_64_r{r}_key{k}_b{b}_reverse_round.cnf"
                )

                if not cnf.exists():
                    raise FileNotFoundError(cnf)
                if not cmap.exists():
                    raise FileNotFoundError(cmap)

                inputs, outputs = parse_reverse_map(cmap)

                units = build_reverse_units(
                    inputs,
                    outputs,
                    r,
                    b,
                    entry["P"],
                    entry["C"],
                )

                write_instance(cnf, out, units)
                print(f"written {out} units={len(units)}")
                total += 1

    print(f"total reverse instances: {total}")


if __name__ == "__main__":
    main()
