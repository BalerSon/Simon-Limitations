#!/usr/bin/env python3
from pathlib import Path
import re
import argparse


def parse_experimental_data(path: Path, rounds: int, key_id: int, blocks: int):
    current_rounds = None
    current_key_id = None
    current_blocks = None
    key_value = None

    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue

        m = re.match(r"Rounds:\s*(\d+)", line)
        if m:
            current_rounds = int(m.group(1))
            current_key_id = None
            current_blocks = None
            continue

        m = re.match(r"Key_(\d+):\s*0x([0-9A-Fa-f]+)", line)
        if m and current_rounds == rounds:
            current_key_id = int(m.group(1))
            if current_key_id == key_id:
                key_value = int(m.group(2), 16)
            current_blocks = None
            continue

        m = re.match(r"Blocks:\s*(\d+)", line)
        if m and current_rounds == rounds and current_key_id == key_id:
            current_blocks = int(m.group(1))
            if current_blocks == blocks and key_value is not None:
                return key_value

    raise ValueError("Key data not found")


def parse_combined_map(path: Path):
    mapping = {}

    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()

        # expected:
        # key[0][0] input 0 aig_lit 2 dimacs_lit 1
        if len(parts) == 7:
            name = parts[0]
            dimacs_lit = int(parts[6])
            mapping[name] = dimacs_lit

    return mapping


def split_key_words(value: int, word_order: str):
    hi_to_lo = [
        (value >> 48) & 0xFFFF,
        (value >> 32) & 0xFFFF,
        (value >> 16) & 0xFFFF,
        value & 0xFFFF,
    ]

    if word_order == "hi-lo":
        return hi_to_lo

    if word_order == "lo-hi":
        return list(reversed(hi_to_lo))

    raise ValueError("word_order must be hi-lo or lo-hi")


def get_bit(word: int, bit_index: int, bit_order: str):
    if bit_order == "msb":
        return (word >> (15 - bit_index)) & 1

    if bit_order == "lsb":
        return (word >> bit_index) & 1

    raise ValueError("bit_order must be msb or lsb")


def unit(lit: int, value: int):
    return lit if value == 1 else -lit


def read_cnf(path: Path):
    lines = path.read_text().splitlines()

    for i, line in enumerate(lines):
        if line.startswith("p cnf"):
            parts = line.split()
            return lines, i, int(parts[2]), int(parts[3])

    raise ValueError(f"No p cnf header in {path}")


def write_fixedkey_instance(src: Path, dst: Path, key_units):
    lines, header_idx, vars_count, clauses_count = read_cnf(src)

    dst.parent.mkdir(parents=True, exist_ok=True)

    with open(dst, "w") as f:
        for i, line in enumerate(lines):
            if i == header_idx:
                f.write(f"p cnf {vars_count} {clauses_count + len(key_units)}\n")
            else:
                f.write(line + "\n")

        for lit in key_units:
            f.write(f"{lit} 0\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, required=True)
    ap.add_argument("--key-id", type=int, required=True)
    ap.add_argument("--blocks", type=int, required=True)
    ap.add_argument("--word-order", choices=["hi-lo", "lo-hi"], default="lo-hi")
    ap.add_argument("--bit-order", choices=["msb", "lsb"], default="msb")
    ap.add_argument("--base", default="/home/balerso/Simon/Simon-Limitations/limitations/BASECNF/with_rk")
    ap.add_argument("--data", default="/home/balerso/Simon/Simon-Limitations/limitations/instruments/data_gen/experimental_data.txt")
    args = ap.parse_args()

    base = Path(args.base)

    key = parse_experimental_data(
        Path(args.data),
        args.rounds,
        args.key_id,
        args.blocks,
    )

    base_instance = (
        base
        / f"{args.rounds}roundsCNF"
        / f"K{args.key_id}"
        / "instances"
        / f"simon32_64_r{args.rounds}_key{args.key_id}_b{args.blocks}_base.cnf"
    )

    combined_map = (
        base
        / f"{args.rounds}roundsCNF"
        / "shared"
        / "maps"
        / f"simon32_64_r{args.rounds}_b{args.blocks}_with_rk_combined_map.txt"
    )

    out = (
        base
        / f"{args.rounds}roundsCNF"
        / f"K{args.key_id}"
        / "instances"
        / f"simon32_64_r{args.rounds}_key{args.key_id}_b{args.blocks}_fixedkey_test.cnf"
    )

    if not base_instance.exists():
        raise FileNotFoundError(f"Base instance not found: {base_instance}")

    if not combined_map.exists():
        raise FileNotFoundError(f"Combined map not found: {combined_map}")

    mapping = parse_combined_map(combined_map)

    key_words = split_key_words(key, args.word_order)

    key_units = []

    for w in range(4):
        for bit in range(16):
            name = f"key[{w}][{bit}]"
            if name not in mapping:
                raise KeyError(f"Missing key variable in map: {name}")

            value = get_bit(key_words[w], bit, args.bit_order)
            key_units.append(unit(mapping[name], value))

    write_fixedkey_instance(base_instance, out, key_units)

    print(f"key = 0x{key:016X}")
    print(f"written {out}")
    print(f"added key units: {len(key_units)}")


if __name__ == "__main__":
    main()
