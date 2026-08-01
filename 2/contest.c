#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <immintrin.h>

typedef struct {
    uint64_t w[4];
} state256_t;

/* -------------------------------------------------
 * Utility functions
 * ------------------------------------------------- */
static inline uint64_t rotl64(uint64_t x, unsigned int n) {
    n &= 63;
    if (n == 0) return x;
    return (x << n) | (x >> (64 - n));
}

void print_state256(const char *label, const state256_t *state) {
    printf("%s = %016llx %016llx %016llx %016llx\n",
           label,
           (unsigned long long)state->w[0],
           (unsigned long long)state->w[1],
           (unsigned long long)state->w[2],
           (unsigned long long)state->w[3]);
}

/* -------------------------------------------------
 * Sub-operations
 * ------------------------------------------------- */

/* 64-bit wise rotation */
void rotate_words_left_64wise(state256_t *state, const unsigned int rot[4]) {
    for (int i = 0; i < 4; i++) {
        state->w[i] = rotl64(state->w[i], rot[i]);
    }
}

/* 256-bit wise XOR */
void xor_constants_256wise(state256_t *state, const uint64_t constants2[4]) {
    for (int i = 0; i < 4; i++) {
        state->w[i] ^= constants2[i];
    }
}

/* 8-bit wise shuffle: out[i] = in[shuffle_map[i]] */
void shuffle_bytes_256(state256_t *state, const uint8_t shuffle_map[32]) {
    uint8_t in[32];
    uint8_t out[32];

    memcpy(in, state, 32);

    for (int i = 0; i < 32; i++) {
        out[i] = in[shuffle_map[i] & 31];
    }

    memcpy(state, out, 32);
}

/* 64-bit wise add */
void add_constants_64wise(state256_t *state, const uint64_t constants1[4]) {
    for (int i = 0; i < 4; i++) {
        state->w[i] += constants1[i];
    }
}


/* -------------------------------------------------
 * 1) One-round permutation:
 *    rotation -> XOR -> shuffling -> add
 *    (uses a fixed reverse-byte shuffle internally)
 * ------------------------------------------------- */
void permute_one_round(state256_t *state,
                       const unsigned int rot[4],
                       const uint8_t shuffle_map[32],
                       const uint64_t constants2[4],
                       const uint64_t constants1[4]) {
    rotate_words_left_64wise(state, rot);
    xor_constants_256wise(state, constants2);
    shuffle_bytes_256(state, shuffle_map);
    add_constants_64wise(state, constants1);

    /*
     * 아래 코드는 1-round 구조와 회전량을 찾을 때 사용한 분석용 코드이다.
     * 최종 제출 코드에서는 실행하지 않으며, 재현 방법을 남기기 위해
     * 주석으로 보존하였다.
     *
     * 연산 번호는 1=ADD, 2=ROT, 3=SHUFFLE, 4=XOR이다. 네 연산의 24가지
     * 순서마다 동일한 임시 회전량을 네 word에 적용하고 결과를 출력한다.
     * 출력 전체를 텍스트 파일로 저장한 뒤 테스트 벡터의 출력 word를
     * grep하면 일치한 연산 순서와 회전량을 확인할 수 있다.
     *
     * (void)rot;
     * const int orders[24][4] = {
     *     {1, 2, 3, 4}, {1, 2, 4, 3}, {1, 3, 2, 4},
     *     {1, 3, 4, 2}, {1, 4, 2, 3}, {1, 4, 3, 2},
     *     {2, 1, 3, 4}, {2, 1, 4, 3}, {2, 3, 1, 4},
     *     {2, 3, 4, 1}, {2, 4, 1, 3}, {2, 4, 3, 1},
     *     {3, 1, 2, 4}, {3, 1, 4, 2}, {3, 2, 1, 4},
     *     {3, 2, 4, 1}, {3, 4, 1, 2}, {3, 4, 2, 1},
     *     {4, 1, 2, 3}, {4, 1, 3, 2}, {4, 2, 1, 3},
     *     {4, 2, 3, 1}, {4, 3, 1, 2}, {4, 3, 2, 1}
     * };
     *
     * for (int order_index = 0; order_index < 24; order_index++) {
     *     for (unsigned int candidate_rot = 1;
     *          candidate_rot <= 63;
     *          candidate_rot++) {
     *         state256_t candidate = *state;
     *         unsigned int trial_rot[4] = {
     *             candidate_rot, candidate_rot,
     *             candidate_rot, candidate_rot
     *         };
     *         char label[32];
     *
     *         for (int step = 0; step < 4; step++) {
     *             switch (orders[order_index][step]) {
     *             case 1:
     *                 add_constants_64wise(&candidate, constants1);
     *                 break;
     *             case 2:
     *                 rotate_words_left_64wise(&candidate, trial_rot);
     *                 break;
     *             case 3:
     *                 shuffle_bytes_256(&candidate, shuffle_map);
     *                 break;
     *             case 4:
     *                 xor_constants_256wise(&candidate, constants2);
     *                 break;
     *             }
     *         }
     *
     *         snprintf(label, sizeof(label), "%d%d%d%d rot=%u",
     *                  orders[order_index][0], orders[order_index][1],
     *                  orders[order_index][2], orders[order_index][3],
     *                  candidate_rot);
     *         print_state256(label, &candidate);
     *     }
     * }
     */
}

/* -------------------------------------------------
 * 2) 20-round permutation
 *    uses the same constants1/constants2 for all rounds
 * ------------------------------------------------- */
void permute_20rounds(state256_t *state,
                     const unsigned int rot[4],
                      const uint8_t shuffle_map[32],
                      const uint64_t constants1[4],
                      const uint64_t constants2[4]) {
    for (int r = 0; r < 20; r++) {
        __m256i x = _mm256_loadu_si256((const __m256i_u *)state->w);
        const __m128i r32 = _mm_loadu_si128((const __m128i_u *)rot);
        const __m256i r0 = _mm256_cvtepu32_epi64(r32);
        const __m256i rinv0 =
            _mm256_sub_epi64(_mm256_set1_epi64x(64), r0);
        const __m256i r1 =
            _mm256_permute4x64_epi64(r0, _MM_SHUFFLE(0, 1, 2, 3));
        const __m256i rinv1 =
            _mm256_permute4x64_epi64(rinv0, _MM_SHUFFLE(0, 1, 2, 3));
        const __m256i vc2 = _mm256_set_epi64x(
            (long long)constants2[3], (long long)constants2[2],
            (long long)constants2[1], (long long)constants2[0]);
        const __m256i vc1 = _mm256_set_epi64x(
            (long long)constants1[3], (long long)constants1[2],
            (long long)constants1[1], (long long)constants1[0]);
        const __m256i vc2_rev = _mm256_set_epi64x(
            (long long)constants2[0], (long long)constants2[1],
            (long long)constants2[2], (long long)constants2[3]);
        const __m256i vc1_rev = _mm256_set_epi64x(
            (long long)constants1[0], (long long)constants1[1],
            (long long)constants1[2], (long long)constants1[3]);
        const __m256i byte_reverse_mask = _mm256_setr_epi8(
            7, 6, 5, 4, 3, 2, 1, 0,
            15, 14, 13, 12, 11, 10, 9, 8,
            7, 6, 5, 4, 3, 2, 1, 0,
            15, 14, 13, 12, 11, 10, 9, 8);

        (void)shuffle_map;

#pragma GCC unroll 10
        for (int i = 0; i < 10; i++) {
            x = _mm256_or_si256(_mm256_sllv_epi64(x, r0),
                                _mm256_srlv_epi64(x, rinv0));
            x = _mm256_xor_si256(x, vc2);
            x = _mm256_shuffle_epi8(x, byte_reverse_mask);
            x = _mm256_add_epi64(x, vc1_rev);

            x = _mm256_or_si256(_mm256_sllv_epi64(x, r1),
                                _mm256_srlv_epi64(x, rinv1));
            x = _mm256_xor_si256(x, vc2_rev);
            x = _mm256_shuffle_epi8(x, byte_reverse_mask);
            x = _mm256_add_epi64(x, vc1);
        }

        _mm256_storeu_si256((__m256i_u *)state->w, x);
        break;
    }
}
// gcc -O3 -Wall -Wextra -mavx2 -o avx_test avx_test.c
/* -------------------------------------------------
 * 3) Main: test + timing
 * ------------------------------------------------- */
int main(void) {
    /* one-round test parameters */
    // TODO: Set rot to proper values.
    const unsigned int rot[4] = { 43, 7, 29, 14 };

    uint8_t shuffle_map[32];
    for (int i = 0; i < 32; i++) {
        shuffle_map[i] = (uint8_t)(31 - i);
    }

    uint64_t constants1[4] = {
        0x8f4a2c1e9b7d3f61ULL,
        0x3c6e9a1d5b7f2840ULL,
        0xa7e2d9c4b1f60853ULL,
        0x5d0f3a8e2c6b4197ULL
    };

    uint64_t constants2[4] = {
        0xe7b92d4a6c1f8035ULL,
        0x1a4f8c3e9d2b6074ULL,
        0xc3f05a2e8d6194b7ULL,
        0x6b2e9d1a4f7c3085ULL
    };

    printf("=== Test 1: one round I/O ===\n");
    /* verify the one-round testvectors in testvector.txt */
    {
        FILE *fv = fopen("testvector.txt", "r");
        if (!fv) {
            perror("fopen testvector.txt for read");
            return 1;
        }

        char line[64];
        int n = 0;
        int all_ok = 1;

        while (fgets(line, sizeof(line), fv)) {
            if (line[0] == '#') {
                unsigned long long in0, in1, in2, in3;
                unsigned long long out0, out1, out2, out3;

                if (!fgets(line, sizeof(line), fv)) break; /* "input" */
                if (fscanf(fv, "%llx %llx %llx %llx",
                           &in0, &in1, &in2, &in3) != 4) {
                    all_ok = 0;
                    break;
                }
                if (!fgets(line, sizeof(line), fv)) break; /* end of numbers line */
                if (!fgets(line, sizeof(line), fv)) break; /* "output" */
                if (fscanf(fv, "%llx %llx %llx %llx",
                           &out0, &out1, &out2, &out3) != 4) {
                    all_ok = 0;
                    break;
                }
                if (!fgets(line, sizeof(line), fv)) break; /* end of output numbers line */

        state256_t vin = { .w = { in0, in1, in2, in3 } };
        state256_t vout = vin;
        permute_one_round(&vout, rot, shuffle_map, constants2, constants1);

                if (vout.w[0] != out0 || vout.w[1] != out1 ||
                    vout.w[2] != out2 || vout.w[3] != out3) {
                    all_ok = 0;
                    break;
                }
                n++;
            }
        }
        fclose(fv);

        if (all_ok) {
            printf("one-round testvector verification: OK (%d pairs checked)\n\n", n);
        } else {
            printf("one-round testvector verification: MISMATCH\n\n");
        }
    }

    printf("=== Test 2: 20 rounds ===\n");

    /* verify the 20-round testvector from testvector_20round.txt */
    {
        FILE *fv20r = fopen("testvector_20round.txt", "r");
        if (!fv20r) {
            perror("fopen testvector_20round.txt for read");
            return 1;
        }

        char dummy[16];
        unsigned long long in0, in1, in2, in3;
        unsigned long long out0, out1, out2, out3;

        /* skip the 'input' line label */
        if (fscanf(fv20r, "%15s", dummy) != 1 ||
            fscanf(fv20r, "%llx %llx %llx %llx",
                   &in0, &in1, &in2, &in3) != 4 ||
            fscanf(fv20r, "%15s", dummy) != 1 ||  /* 'output' */
            fscanf(fv20r, "%llx %llx %llx %llx",
                   &out0, &out1, &out2, &out3) != 4) {
            fprintf(stderr, "Failed to parse testvector_20round.txt\n");
            fclose(fv20r);
            return 1;
        }
        fclose(fv20r);

        state256_t vin = { .w = { in0, in1, in2, in3 } };
        state256_t vout = vin;
        permute_20rounds(&vout, rot, shuffle_map, constants1, constants2);

        int ok = 1;
        if (vout.w[0] != out0 || vout.w[1] != out1 ||
            vout.w[2] != out2 || vout.w[3] != out3) {
            ok = 0;
        }

        if (ok) {
            printf("20-round testvector verification: OK\n\n");
        } else {
            printf("20-round testvector verification: MISMATCH\n\n");
        }
    }

    printf("=== Test 3: timing of 20-round permutation ===\n");
    {
        const int iterations = 1000000;
        state256_t bench = {
            .w = {
                0x0123456789abcdefULL,
                0xfedcba9876543210ULL,
                0x0f1e2d3c4b5a6978ULL,
                0x8877665544332211ULL
            }
        };

        clock_t start = clock();
        for (int i = 0; i < iterations; i++) {
            permute_20rounds(&bench, rot, shuffle_map, constants1, constants2);
        }
        clock_t end = clock();

        double elapsed_sec = (double)(end - start) / CLOCKS_PER_SEC;
        double per_call_us = (elapsed_sec * 1000000.0) / iterations;

        print_state256("benchmark final state", &bench);
        printf("iterations           = %d\n", iterations);
        printf("total elapsed time   = %.6f sec\n", elapsed_sec);
        printf("average per 20rounds = %.6f us\n", per_call_us);
    }

    return 0;
}
