#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

#include "simon.c"

uint32_t random_u32() {
    uint32_t x = 0;

    x |= ((uint32_t)(rand() & 0xFFFF)) << 16;
    x |= ((uint32_t)(rand() & 0xFFFF));

    return x;
}

uint64_t random_u64() {
    uint64_t x = 0;

    x |= ((uint64_t)random_u32()) << 32;
    x |= ((uint64_t)random_u32());

    return x;
}

int main() {
    srand(12345);

    FILE *file = fopen("experimental_data.txt", "w");
    if (file == NULL) {
        printf("Error: cannot open file");
        return 1;
    }

    uint64_t keys[5];
    for (int k = 0; k < 5; k++) {
        uint64_t key = random_u64();
        keys[k] = key;
    }

    uint32_t plaintexts[8];
    for (int p = 0; p < 8; p++) {
        uint32_t plaintext = random_u32();
        plaintexts[p] = plaintext;
    }

    int blocks_count[4] = {1, 2, 4, 8};

    for (int rounds = 10; rounds < 15; rounds++) {
        fprintf(file, "Rounds:    %d\n", rounds);
        for (int k = 0; k < 5; k++) {
            uint64_t key = keys[k];
            fprintf(file, "Key_%d:    0x%016llX\n\n", k + 1, (unsigned long long)key);
            for (int b = 0; b < 4; b++) {
                int blocks = blocks_count[b];
                fprintf(file, "Blocks:    %d\n", blocks);
                for (int p = 0; p < blocks; p++) {
                    uint32_t plaintext = plaintexts[p];
                    fprintf(file, "P_%d:    0x%08X\n", p + 1, plaintext);
                    uint32_t ciphertext = simon_encrypt(plaintext, key, rounds);
                    fprintf(file, "C_%d:    0x%08X\n\n", p + 1, ciphertext);
                }
                fprintf(file, "\n");
            }
            fprintf(file, "\n");
        }
        fprintf(file, "\n");
    }
    fclose(file);
    return 0;
}