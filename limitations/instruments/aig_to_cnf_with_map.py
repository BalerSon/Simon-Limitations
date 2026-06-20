#!/usr/bin/env python3
from pathlib import Path
import argparse


def aig_not(lit: int) -> int:
    """
    AIGER negation:
      0 <-> 1
      2*v <-> 2*v+1
    """
    return lit ^ 1


def aig_lit_to_dimacs(lit: int):
    """
    Convert AIGER literal to DIMACS literal.

    Return:
      None for constant false/true is handled separately in clause conversion.
      int for normal DIMACS literal.
    """
    if lit == 0:
        return None
    if lit == 1:
        return None

    var = lit // 2
    return -var if lit % 2 else var


def aig_clause_to_dimacs_clause(aig_clause):
    """
    Convert a clause written in AIGER literals to DIMACS.

    AIGER constants:
      0 = false
      1 = true

    If clause contains true, clause is tautological and should be skipped.
    False literals are removed.
    """
    dimacs_clause = []

    for lit in aig_clause:
        if lit == 1:
            return None  # tautology, skip whole clause

        if lit == 0:
            continue  # false literal, remove it

        dimacs_clause.append(aig_lit_to_dimacs(lit))

    return dimacs_clause


def parse_aag(path: Path):
    lines = path.read_text().splitlines()

    if not lines:
        raise ValueError(f"Empty file: {path}")

    header = lines[0].split()

    if header[0] != "aag":
        raise ValueError(f"Expected AAG file starting with 'aag', got: {header[0]}")

    M = int(header[1])
    I = int(header[2])
    L = int(header[3])
    O = int(header[4])
    A = int(header[5])

    if L != 0:
        raise ValueError("This script does not support latches")

    idx = 1

    inputs = []
    for _ in range(I):
        inputs.append(int(lines[idx].strip()))
        idx += 1

    outputs = []
    for _ in range(O):
        outputs.append(int(lines[idx].strip()))
        idx += 1

    ands = []
    for _ in range(A):
        lhs, rhs0, rhs1 = map(int, lines[idx].split())
        ands.append((lhs, rhs0, rhs1))
        idx += 1

    return M, I, O, A, inputs, outputs, ands


def build_cnf(ands):
    clauses = []

    for lhs, rhs0, rhs1 in ands:
        # lhs <-> rhs0 AND rhs1
        #
        # CNF:
        #   ~lhs OR rhs0
        #   ~lhs OR rhs1
        #    lhs OR ~rhs0 OR ~rhs1

        aig_clauses = [
            [aig_not(lhs), rhs0],
            [aig_not(lhs), rhs1],
            [lhs, aig_not(rhs0), aig_not(rhs1)],
        ]

        for aig_clause in aig_clauses:
            dimacs_clause = aig_clause_to_dimacs_clause(aig_clause)

            if dimacs_clause is None:
                continue

            clauses.append(dimacs_clause)

    return clauses


def dimacs_lit_for_map(aig_lit: int):
    if aig_lit == 0:
        return "CONST0"
    if aig_lit == 1:
        return "CONST1"

    var = aig_lit // 2
    return str(-var if aig_lit % 2 else var)


def write_cnf(path: Path, num_vars: int, clauses):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write(f"p cnf {num_vars} {len(clauses)}\n")

        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")


def write_full_map(path: Path, inputs, outputs):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write("# Full map for mapped CNF\n")
        f.write("# Format:\n")
        f.write("# input  <input_index>  aig_lit <aig_literal>  dimacs_lit <dimacs_literal>\n")
        f.write("# output <output_index> aig_lit <aig_literal>  dimacs_lit <dimacs_literal>\n\n")

        f.write("# Inputs\n")
        for i, lit in enumerate(inputs):
            f.write(f"input {i} aig_lit {lit} dimacs_lit {dimacs_lit_for_map(lit)}\n")

        f.write("\n# Outputs\n")
        for i, lit in enumerate(outputs):
            f.write(f"output {i} aig_lit {lit} dimacs_lit {dimacs_lit_for_map(lit)}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aag", required=True)
    parser.add_argument("--cnf", required=True)
    parser.add_argument("--map", required=True)
    args = parser.parse_args()

    aag_path = Path(args.aag)
    cnf_path = Path(args.cnf)
    map_path = Path(args.map)

    M, I, O, A, inputs, outputs, ands = parse_aag(aag_path)
    clauses = build_cnf(ands)

    write_cnf(cnf_path, M, clauses)
    write_full_map(map_path, inputs, outputs)

    print(f"AAG:     {aag_path}")
    print(f"CNF:     {cnf_path}")
    print(f"MAP:     {map_path}")
    print(f"vars:    {M}")
    print(f"inputs:  {I}")
    print(f"outputs: {O}")
    print(f"ands:    {A}")
    print(f"clauses: {len(clauses)}")


if __name__ == "__main__":
    main()
