from pathlib import Path

rounds_list = [10, 11, 12, 13, 14]
blocks_list = [1, 2, 4, 8]

base = Path("/home/balerso/Simon/Simon-Limitations/limitations/BASECNF/with_rk")

for rounds in rounds_list:
    for blocks in blocks_list:
        shared = base / f"{rounds}roundsCNF" / "shared"
        maps_dir = shared / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)

        map_path = maps_dir / f"simon32_64_r{rounds}_b{blocks}_with_rk_map.txt"

        with open(map_path, "w") as f:
            f.write(f"# Map for SIMON32/64, rounds={rounds}, blocks={blocks}, with_rk\n")
            f.write("# Format: name output_index\n\n")

            out = 0

            f.write("# Ciphertext outputs\n")
            for b in range(blocks):
                for word in range(2):
                    for bit in range(16):
                        f.write(f"ct[{b}][{word}][{bit}] output {out}\n")
                        out += 1

            f.write("\n# Round key outputs\n")
            for r in range(rounds):
                for bit in range(16):
                    f.write(f"rk[{r}][{bit}] output {out}\n")
                    out += 1

        print(f"written {map_path}")
