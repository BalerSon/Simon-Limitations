#include <stdio.h>
#include <stdint.h>
#include <assert.h>

#define BLOCKS_COUNT 1
#define MAX_ROUNDS_COUNT 32

typedef uint16_t word;
typedef uint32_t block;
typedef uint64_t key;

const uint64_t z_sequence = 0x19c3522fb386a45f;

void print_round_keys(word round_keys[MAX_ROUNDS_COUNT], const char* title) {
    printf("\n%s:\n", title);
    printf("----------------------------------------\n");
    for (int i = 0; i < MAX_ROUNDS_COUNT; i++) {
        printf("> Round %2d key: k[%2d] = 0x%04X", i, i, round_keys[i]);
        
        if ((i + 1) % 4 == 0) printf("\n");
        else printf("  ");
    }
    printf("----------------------------------------\n");
}

word left_shift(word x, int n) {
    return (x << n) | (x >> (16 - n));
}

word right_shift(word x, int n) {
    return (x >> n) | (x << (16 - n));
}

void simon_round(word *left, word *right, word round_key, int round_num) {
    word temp = *left;
    word f_x = (left_shift(*left, 1) & left_shift(*left, 8)) ^ left_shift(*left, 2);
    
    *left = *right ^ f_x ^ round_key;
    *right = temp;
}

void key_schedule(word key_words[4], word round_keys[MAX_ROUNDS_COUNT]) {
    word c = 0xFFFC;
    int j = 0;

    round_keys[0] = key_words[3];
    round_keys[1] = key_words[2];
    round_keys[2] = key_words[1];
    round_keys[3] = key_words[0];

    for (int i = 4; i < MAX_ROUNDS_COUNT; i++) {
        word temp = right_shift(round_keys[i - 1], 3);
        temp = temp ^ round_keys[i - 3];
        temp = temp ^ right_shift(temp, 1);

        int bit_index = (i - 4) % 62;
        word z_bit = (z_sequence >> bit_index) & 1;
        
        round_keys[i] = round_keys[i - 4] ^ temp ^ z_bit ^ c;
    }
}

block simon_encrypt(block plaintext, key k, int rounds) {
    word key_words[4];
    word round_keys[MAX_ROUNDS_COUNT];

    key_words[0] = (k >> 48) & 0xFFFF;
    key_words[1] = (k >> 32) & 0xFFFF;
    key_words[2] = (k >> 16) & 0xFFFF;
    key_words[3] = k & 0xFFFF;

    key_schedule(key_words, round_keys);

    // print_round_keys(round_keys, "ALL ROUND KEYS");

    word left = (plaintext >> 16) & 0xFFFF;
    word right = plaintext & 0xFFFF;

    for (int round = 0; round < rounds; round++) {
        simon_round(&left, &right, round_keys[round], round);
    }

    block ciphertext = ((block)left << 16) | right;

    return ciphertext;
}

// void test_simon() {
//     block plaintext = 0x65656877;
//     key k = 0x1918111009080100;
//     block desired_ciphertext = 0xC69BE9BB;
//     int rounds = 32;

//     block received_ciphertext = simon_encrypt(plaintext, k, rounds);
    
//     printf("\n==========Results==========\n");
//     printf("Plaintext: %08X\n", plaintext);
//     printf("Desired ciphertext: %08X\n", desired_ciphertext);
//     printf("Received ciphertext: %08X\n", received_ciphertext);
//     printf("Test: %s\n", received_ciphertext == desired_ciphertext ? "PASSED" : "FAILED");
// }

// int main() {
//     test_simon();
//     return 0;
// }