#!/usr/bin/env python3
from pathlib import Path
import re
import argparse
import subprocess

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

    return data


def parse_inputs(map_path):
    inputs = {}
    in_re = re.compile(r"input\s+(\d+)\s+aig_lit\s+-?\d+\s+dimacs_lit\s+(-?\d+)")

    for raw in Path(map_path).read_text().splitlines():
        line = raw.strip()
        m = in_re.match(line)
        if m:
            inputs[int(m.group(1))] = int(m.group(2))

    return inputs


def split_key_words(key64):
    # В experimental_data ключ записан как 0xA847A1951BEDCF3B.
    # В Cryptol key = [0xCF3B, 0x1BED, 0xA195, 0xA847],
    # поэтому берём слова от младшего к старшему.
    return [
        key64 & 0xFFFF,
        (key64 >> 16) & 0xFFFF,
        (key64 >> 32) & 0xFFFF,
        (key64 >> 48) & 0xFFFF,
    ]


def bit_msb(word, bit):
    return (word >> (15 - bit)) & 1


def key_bits_from_key64(key64):
    bits = []
    for word in split_key_words(key64):
        for bit in range(16):
            bits.append(bit_msb(word, bit))
    return bits


def unit(lit, value):
    return lit if value else -lit


def read_cnf(path):
    lines = Path(path).read_text().splitlines()

    for i, line in enumerate(lines):
        if line.startswith("p cnf"):
            parts = line.split()
            return lines, i, int(parts[2]), int(parts[3])

    raise ValueError(f"No p cnf header in {path}")


def write_fixedkey_instance(src, dst, key_units):
    lines, header_idx, nvars, nclauses = read_cnf(src)

    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    with dst.open("w") as f:
        for i, line in enumerate(lines):
            if i == header_idx:
                f.write(f"p cnf {nvars} {nclauses + len(key_units)}\n")
            else:
                f.write(line + "\n")

        for lit in key_units:
            f.write(f"{lit} 0\n")


def run_kissat(kissat, cnf, timeout):
    try:
        res = subprocess.run(
            ["timeout", str(timeout), str(kissat), str(cnf)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as e:
        return "ERROR", str(e)

    out = res.stdout

    if "s SATISFIABLE" in out:
        return "SAT", out
    if "s UNSATISFIABLE" in out:
        return "UNSAT", out
    if res.returncode == 124:
        return "TIMEOUT", out

    return "UNKNOWN", out


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
    ap.add_argument(
        "--kissat",
        default="/home/balerso/Simon/Simon-Limitations/limitations/instruments/bin/kissat",
    )
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument(
        "--results",
        default="/home/balerso/Simon/Simon-Limitations/limitations/instruments/reverse_round/reverse_fixedkey_check_results.txt",
    )
    args = ap.parse_args()

    base = Path(args.base)
    data = parse_experimental_data(args.data)
    kissat = Path(args.kissat)
    results_path = Path(args.results)

    results_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    sat = 0
    bad = 0

    with results_path.open("w") as rf:
        for r in ROUNDS_LIST:
            for k in KEYS_LIST:
                for b in BLOCKS_LIST:
                    entry = data[r][k][b]
                    key64 = entry["key"]

                    instance = (
                        base
                        / f"{r}roundsCNF"
                        / f"K{k}"
                        / "instances"
                        / f"simon32_64_r{r}_key{k}_b{b}_reverse_round.cnf"
                    )

                    fixed = (
                        base
                        / f"{r}roundsCNF"
                        / f"K{k}"
                        / "instances"
                        / f"simon32_64_r{r}_key{k}_b{b}_reverse_round_fixedkey.cnf"
                    )

                    cmap = (
                        base
                        / f"{r}roundsCNF"
                        / "shared"
                        / "maps"
                        / f"simon32_64_r{r}_b{b}_reverse_rk_combined_map.txt"
                    )

                    if not instance.exists():
                        raise FileNotFoundError(instance)
                    if not cmap.exists():
                        raise FileNotFoundError(cmap)

                    inputs = parse_inputs(cmap)
                    bits = key_bits_from_key64(key64)

                    key_units = []
                    for idx, bit in enumerate(bits):
                        if idx not in inputs:
                            raise KeyError(f"input {idx} not found in {cmap}")
                        key_units.append(unit(inputs[idx], bit))

                    write_fixedkey_instance(instance, fixed, key_units)

                    status, solver_out = run_kissat(kissat, fixed, args.timeout)

                    line = f"r={r} k={k} b={b} status={status} fixed={fixed}"
                    print(line)
                    rf.write(line + "\n")

                    total += 1
                    if status == "SAT":
                        sat += 1
                    else:
                        bad += 1
                        rf.write("---- solver output ----\n")
                        rf.write(solver_out + "\n")
                        rf.write("-----------------------\n")

        summary = f"SUMMARY total={total} SAT={sat} BAD={bad}"
        print(summary)
        rf.write(summary + "\n")


if __name__ == "__main__":
    main()
