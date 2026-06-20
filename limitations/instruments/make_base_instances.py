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

def parse_combined_map(path):
    mapping = {}

    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) == 7:
            mapping[parts[0]] = int(parts[6])

    return mapping

def split32_hi_lo(x):
    return [(x >> 16) & 0xFFFF, x & 0xFFFF]

def bit_msb(word, bit):
    return (word >> (15 - bit)) & 1

def unit(lit, value):
    return lit if value else -lit

def build_units(mapping, blocks, plaintexts, ciphertexts):
    units = []

    for b in range(blocks):
        p_words = split32_hi_lo(plaintexts[b])
        c_words = split32_hi_lo(ciphertexts[b])

        for w in range(2):
            for bit in range(16):
                p_name = f"pt[{b}][{w}][{bit}]"
                p_val = bit_msb(p_words[w], bit)
                units.append(unit(mapping[p_name], p_val))

                c_name = f"ct[{b}][{w}][{bit}]"
                c_val = bit_msb(c_words[w], bit)
                units.append(unit(mapping[c_name], c_val))

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

    with open(dst, "w") as f:
        for i, line in enumerate(lines):
            if i == header_idx:
                f.write(f"p cnf {nvars} {nclauses + len(units)}\n")
            else:
                f.write(line + "\n")

        for lit in units:
            f.write(f"{lit} 0\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="/home/balerso/Simon/Simon-Limitations/limitations/BASECNF/with_rk")
    ap.add_argument("--data", default="/home/balerso/Simon/Simon-Limitations/limitations/instruments/data_gen/experimental_data.txt")
    args = ap.parse_args()

    base = Path(args.base)
    data = parse_experimental_data(args.data)

    total = 0

    for r in ROUNDS_LIST:
        for k in KEYS_LIST:
            for b in BLOCKS_LIST:
                entry = data[r][k][b]

                shared = base / f"{r}roundsCNF" / "shared"

                cnf = shared / "cnfs" / f"simon32_64_r{r}_b{b}_with_rk_opt_mapped.cnf"
                cmap = shared / "maps" / f"simon32_64_r{r}_b{b}_with_rk_combined_map.txt"

                out = (
                    base
                    / f"{r}roundsCNF"
                    / f"K{k}"
                    / "instances"
                    / f"simon32_64_r{r}_key{k}_b{b}_base.cnf"
                )

                if not cnf.exists():
                    raise FileNotFoundError(cnf)
                if not cmap.exists():
                    raise FileNotFoundError(cmap)

                mapping = parse_combined_map(cmap)

                units = build_units(
                    mapping,
                    b,
                    entry["P"],
                    entry["C"],
                )

                write_instance(cnf, out, units)
                print(f"written {out} units={len(units)}")
                total += 1

    print(f"total instances: {total}")

if __name__ == "__main__":
    main()
