#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ZSEQ = "11111010001001010110000111001101111101000100101011000011100110"


def parse_dimacs(path: Path):
    comments = []
    clauses = []
    num_vars = None
    num_clauses = None

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("c"):
                comments.append(line)
                continue

            if line.startswith("p cnf"):
                parts = line.split()
                num_vars = int(parts[2])
                num_clauses = int(parts[3])
                continue

            clauses.append(line)

    if num_vars is None or num_clauses is None:
        raise ValueError(f"CNF header not found in {path}")

    return comments, num_vars, num_clauses, clauses


def lit_neg(lit: int) -> int:
    return -lit


def xor2_clauses(x: int, y: int, z: int):
    """
    Кодирует z = x xor y.
    x и y могут быть отрицательными литералами.
    z — новая положительная DIMACS-переменная.
    """
    return [
        [ x,  y, -z],
        [ x, -y,  z],
        [-x,  y,  z],
        [-x, -y, -z],
    ]


def add_xor_sum_equals(lits, const, next_var):
    """
    lits[0] xor lits[1] xor ... xor lits[n-1] = const

    lits могут быть отрицательными DIMACS-литералами.
    Например -201 означает не переменную 201, а её отрицание.
    """
    if len(lits) < 2:
        raise ValueError("Need at least two literals for XOR")

    clauses = []

    # t = lits[0] xor lits[1]
    t = next_var
    next_var += 1
    clauses.extend(xor2_clauses(lits[0], lits[1], t))

    # t = t xor lits[k]
    for lit in lits[2:]:
        new_t = next_var
        next_var += 1
        clauses.extend(xor2_clauses(t, lit, new_t))
        t = new_t

    # t == const
    if const == 1:
        clauses.append([t])
    else:
        clauses.append([-t])

    return clauses, next_var


def c3_bit(j: int) -> int:
    """
    c3 = 3:[16] = 0000000000000011
    При порядке битов rk[i][0]..rk[i][15]:
    j=14 и j=15 равны 1.
    """
    return 1 if j in (14, 15) else 0


def z_bit(i: int, j: int) -> int:
    """
    z = zero:[15] # [zSeq @ ((i-4)%62)]
    Поэтому z может быть 1 только в последнем бите j=15.
    """
    if j != 15:
        return 0
    return int(ZSEQ[(i - 4) % 62])


def build_rk_schedule_constraints(rk, rounds, first_free_var, shift_direction):
    """
    Добавляет ограничения key schedule.

    Для каждого i >= 4:

      tmp = rk[i-1] >>> 3
      p   = tmp xor rk[i-3]
      q   = p xor (p >>> 1)
      rk[i] = ~rk[i-4] xor q xor z xor c3

    Параметр shift_direction нужен из-за возможной разницы в порядке битов:
      cryptol-right: (x >>> s)[j] = x[(j - s) mod 16]
      reversed:      (x >>> s)[j] = x[(j + s) mod 16]
    """
    clauses = []
    next_var = first_free_var

    if len(rk) < rounds:
        raise ValueError(f"rk map has {len(rk)} rounds, but rounds={rounds}")

    for row_id, row in enumerate(rk):
        if len(row) != 16:
            raise ValueError(f"rk[{row_id}] must contain 16 literals")

    def idx(j, s):
        if shift_direction == "cryptol-right":
            return (j - s) % 16
        if shift_direction == "reversed":
            return (j + s) % 16
        raise ValueError(f"Unknown shift direction: {shift_direction}")

    for i in range(4, rounds):
        for j in range(16):
            lits = [
                rk[i][j],
                rk[i - 4][j],
                rk[i - 1][idx(j, 3)],
                rk[i - 3][j],
                rk[i - 1][idx(j, 4)],
                rk[i - 3][idx(j, 1)],
            ]

            const = 1 ^ z_bit(i, j) ^ c3_bit(j)

            new_clauses, next_var = add_xor_sum_equals(lits, const, next_var)
            clauses.extend(new_clauses)

    return clauses, next_var


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cnf", required=True, help="Input base CNF")
    ap.add_argument("--rk-map", required=True, help="JSON with rk literals")
    ap.add_argument("--rounds", type=int, required=True)
    ap.add_argument("--out", required=True, help="Output limited CNF")
    ap.add_argument(
        "--shift-direction",
        choices=["cryptol-right", "reversed"],
        default="cryptol-right",
        help="Bit indexing convention for >>>. Try reversed if the result becomes UNSAT.",
    )
    args = ap.parse_args()

    cnf_path = Path(args.cnf)
    rk_map_path = Path(args.rk_map)
    out_path = Path(args.out)

    comments, old_vars, old_clause_count, old_clauses = parse_dimacs(cnf_path)

    with rk_map_path.open("r", encoding="utf-8") as f:
        rk_data = json.load(f)

    rk = rk_data["rk"]

    first_free_var = old_vars + 1

    added_clauses, next_free_var = build_rk_schedule_constraints(
        rk=rk,
        rounds=args.rounds,
        first_free_var=first_free_var,
        shift_direction=args.shift_direction,
    )

    new_vars = next_free_var - 1
    new_clause_count = len(old_clauses) + len(added_clauses)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for c in comments:
            f.write(c + "\n")

        f.write("c added RK_SCHEDULE constraints\n")
        f.write(f"c source_cnf {cnf_path}\n")
        f.write(f"c rk_map {rk_map_path}\n")
        f.write(f"c rounds {args.rounds}\n")
        f.write(f"c shift_direction {args.shift_direction}\n")
        f.write(f"c added_vars {new_vars - old_vars}\n")
        f.write(f"c added_clauses {len(added_clauses)}\n")
        f.write(f"p cnf {new_vars} {new_clause_count}\n")

        for clause in old_clauses:
            f.write(clause + "\n")

        for clause in added_clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")

    print("OK")
    print(f"input:          {cnf_path}")
    print(f"output:         {out_path}")
    print(f"rk_map:         {rk_map_path}")
    print(f"rounds:         {args.rounds}")
    print(f"shift:          {args.shift_direction}")
    print(f"old vars:       {old_vars}")
    print(f"new vars:       {new_vars}")
    print(f"added vars:     {new_vars - old_vars}")
    print(f"old clauses:    {len(old_clauses)}")
    print(f"new clauses:    {new_clause_count}")
    print(f"added clauses:  {len(added_clauses)}")


if __name__ == "__main__":
    main()