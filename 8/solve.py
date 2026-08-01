#!/usr/bin/env python3
"""
2026 암호분석경진대회 8번 풀이 코드.

입력 파일 plaintext.bin, ciphertext.bin, leaked.txt가 같은 디렉터리에 있다고 가정한다.
외부 패키지는 필요 없다.

주의: 제공된 데이터는 문제 PDF의 k6 표기를 그대로 쓰면 검증되지 않고,
      k6에도 MixColumns를 한 등가 라운드키를 써야 전체 50,000쌍이 검증된다.
      아래 round_keys(..., data_compatible=True)가 이 실제 데이터 생성 방식을 반영한다.
"""
# K = 2923be84e16cd6ae529049f1f1bbe9eb

from __future__ import annotations

import itertools
import re
from pathlib import Path

SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
INV_SBOX = [0] * 256
for i, v in enumerate(SBOX):
    INV_SBOX[v] = i


def xtime(a: int) -> int:
    return (((a << 1) ^ 0x1B) & 0xFF) if (a & 0x80) else ((a << 1) & 0xFF)


def gmul(a: int, b: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = xtime(a)
        b >>= 1
    return r

MUL2  = [gmul(x, 0x02) for x in range(256)]
MUL3  = [gmul(x, 0x03) for x in range(256)]
MUL9  = [gmul(x, 0x09) for x in range(256)]
MUL11 = [gmul(x, 0x0B) for x in range(256)]
MUL13 = [gmul(x, 0x0D) for x in range(256)]
MUL14 = [gmul(x, 0x0E) for x in range(256)]


def mix_single_col(c: list[int]) -> list[int]:
    a0, a1, a2, a3 = c
    return [
        MUL2[a0] ^ MUL3[a1] ^ a2 ^ a3,
        a0 ^ MUL2[a1] ^ MUL3[a2] ^ a3,
        a0 ^ a1 ^ MUL2[a2] ^ MUL3[a3],
        MUL3[a0] ^ a1 ^ a2 ^ MUL2[a3],
    ]


def inv_mix_single_col(c: list[int]) -> list[int]:
    a0, a1, a2, a3 = c
    return [
        MUL14[a0] ^ MUL11[a1] ^ MUL13[a2] ^ MUL9[a3],
        MUL9[a0] ^ MUL14[a1] ^ MUL11[a2] ^ MUL13[a3],
        MUL13[a0] ^ MUL9[a1] ^ MUL14[a2] ^ MUL11[a3],
        MUL11[a0] ^ MUL13[a1] ^ MUL9[a2] ^ MUL14[a3],
    ]


def mix_columns(s: list[int]) -> list[int]:
    out = [0] * 16
    for col in range(4):
        out[4*col:4*col+4] = mix_single_col(s[4*col:4*col+4])
    return out


def shift_rows(s: list[int]) -> list[int]:
    # AES 표준 column-major 상태: index = row + 4*column
    out = [0] * 16
    for r in range(4):
        for c in range(4):
            out[r + 4*c] = s[r + 4*((c + r) & 3)]
    return out


def sub_bytes(s: list[int]) -> list[int]:
    return [SBOX[x] for x in s]


def core(s: list[int]) -> list[int]:
    return mix_columns(shift_rows(sub_bytes(s)))


def xor(a: list[int], b: list[int]) -> list[int]:
    return [x ^ y for x, y in zip(a, b)]

P1 = [5,8,6,3, 15,14,13,12, 11,10,2,1, 0,4,7,9]
P2 = [6,10,5,12, 3,2,15,9, 1,4,8,11, 13,7,0,14]
P3 = [10,3,1,7, 8,11,9,5, 2,6,12,15, 4,0,14,13]
P4 = [14,11,7,5, 10,1,13,12, 0,6,2,4, 8,15,3,9]
P5 = [15,10,12,1, 14,8,13,4, 2,3,0,5, 11,7,6,9]
P6 = [1,5,7,14, 15,8,0,4, 9,13,3,6, 12,2,10,11]


def round_keys(K: bytes | list[int], *, data_compatible: bool = True) -> list[list[int]]:
    K = list(K)
    keys = [None] * 7
    keys[0] = K[:]
    keys[1] = mix_columns([K[i] for i in P1])
    keys[2] = mix_columns([K[i] for i in P2])
    keys[3] = [K[i] for i in P3]
    keys[4] = [K[i] for i in P4]
    keys[5] = mix_columns([K[i] for i in P5])
    keys[6] = [K[i] for i in P6]
    if data_compatible:
        # ciphertext.bin 검증에 필요한 실제 생성 방식: k6도 MC(P6(K))로 들어간다.
        keys[6] = mix_columns(keys[6])
    return keys


def encrypt_block(P: bytes | list[int], K: bytes | list[int], *, states: bool = False) -> bytes | tuple[bytes, list[list[int]]]:
    x = list(P)
    st = [x[:]]
    for rk in round_keys(K):
        x = xor(core(x), rk)
        st.append(x[:])
    return (bytes(x), st) if states else bytes(x)


def byte_candidates(pattern: str) -> list[int]:
    return [x for x in range(256) if all(a == '-' or a == b for a, b in zip(pattern, f'{x:08b}'))]


def read_leak(path: Path) -> dict[tuple[int, int], list[int]]:
    leak: dict[tuple[int, int], list[int]] = {}
    rx = re.compile(r'X\^(\d+)\[(\d+)\]: ([01-]{8})')
    for line in path.read_text().splitlines():
        m = rx.match(line.strip())
        if m:
            leak[(int(m.group(1)), int(m.group(2)))] = byte_candidates(m.group(3))
    return leak


def leak_ok(leak: dict[tuple[int, int], list[int]], r: int, state: list[int]) -> bool:
    for (rr, i), vals in leak.items():
        if rr == r and state[i] not in vals:
            return False
    return True


def recover_key(pt: bytes, ct: bytes, leak: dict[tuple[int, int], list[int]], trace_index: int = 28178) -> bytes:
    P = list(pt[16*trace_index:16*trace_index+16])
    C = ct[16*trace_index:16*trace_index+16]

    base1 = core(P)
    K0 = base1[0] ^ leak[(1, 0)][0]

    X2_choices = [leak[(2, i)] for i in range(4)]
    X3_choices = [leak[(3, i)] for i in range(16)]
    X4_diag_choices = [leak[(4, i)] for i in (0, 5, 10, 15)]

    candidates: list[bytes] = []

    for X3_tuple in itertools.product(*X3_choices):
        X3 = list(X3_tuple)
        A = [inv_mix_single_col(X3[4*c:4*c+4]) for c in range(4)]
        F3 = core(X3)

        K10_opts = [x ^ F3[0]  for x in X4_diag_choices[0]]
        K11_opts = [x ^ F3[5]  for x in X4_diag_choices[1]]
        K12_opts = [x ^ F3[10] for x in X4_diag_choices[2]]
        K13_opts = [x ^ F3[15] for x in X4_diag_choices[3]]

        for x20, x21, x22, x23 in itertools.product(*X2_choices):
            # round 1, column 0: InvMC(X2_col0) = SB(SR(X1))_col0 xor [K5,K8,K6,K3]
            B0 = inv_mix_single_col([x20, x21, x22, x23])
            K5 = B0[0] ^ SBOX[base1[0] ^ K0]
            K8_from_r1 = B0[1] ^ SBOX[base1[5] ^ K5]

            # round 2, known X2[0..3] positions
            K6 = A[0][0] ^ SBOX[x20]
            K7 = A[3][1] ^ SBOX[x21]
            K8 = A[2][2] ^ SBOX[x22]
            K9 = A[1][3] ^ SBOX[x23]
            if K8_from_r1 != K8:
                continue

            valid_K10 = [k for k in K10_opts if (B0[2] ^ SBOX[base1[10] ^ k]) == K6]
            if not valid_K10:
                continue

            for K10 in valid_K10:
                for K11 in K11_opts:
                    for K12 in K12_opts:
                        for K13 in K13_opts:
                            K = [None] * 16
                            for i, v in [
                                (0,K0),(5,K5),(6,K6),(7,K7),(8,K8),(9,K9),
                                (10,K10),(11,K11),(12,K12),(13,K13),
                            ]:
                                K[i] = v

                            x2 = [None] * 16
                            x2[0:4] = [x20, x21, x22, x23]
                            x2[5]  = INV_SBOX[A[0][1] ^ K10]
                            x2[10] = INV_SBOX[A[0][2] ^ K5]
                            x2[15] = INV_SBOX[A[0][3] ^ K12]
                            x2[7]  = INV_SBOX[A[2][3] ^ K11]
                            x2[12] = INV_SBOX[A[3][0] ^ K13]
                            x2[6]  = INV_SBOX[A[3][2] ^ K0]

                            # K3 is the only unknown in X2[4] and in the 4th equation of column 1.
                            for K3 in range(256):
                                x24 = INV_SBOX[A[1][0] ^ K3]
                                B1 = inv_mix_single_col([x24, x2[5], x2[6], x2[7]])
                                if B1[3] != (SBOX[base1[3] ^ K3] ^ K12):
                                    continue

                                K[3] = K3
                                x2[4] = x24

                                K14 = base1[14] ^ INV_SBOX[B1[2] ^ K13]
                                if B1[1] != (SBOX[base1[9] ^ K9] ^ K14):
                                    continue
                                K15 = base1[15] ^ INV_SBOX[B0[3] ^ K3]
                                K4  = base1[4]  ^ INV_SBOX[B1[0] ^ K15]
                                K[4], K[14], K[15] = K4, K14, K15

                                x2[11] = INV_SBOX[A[3][3] ^ K14]
                                x2[13] = INV_SBOX[A[2][1] ^ K4]
                                x2[14] = INV_SBOX[A[1][2] ^ K15]

                                B3 = inv_mix_single_col([x2[12], x2[13], x2[14], x2[15]])
                                if B3[0] != (SBOX[base1[12] ^ K12] ^ K0):
                                    continue
                                K1 = base1[1] ^ INV_SBOX[B3[1] ^ K4]
                                if B3[2] != (SBOX[base1[6] ^ K6] ^ K7):
                                    continue
                                if B3[3] != (SBOX[base1[11] ^ K11] ^ K9):
                                    continue
                                K[1] = K1

                                x2[8] = INV_SBOX[A[2][0] ^ K1]
                                for K2 in range(256):
                                    x2[9] = INV_SBOX[A[1][1] ^ K2]
                                    B2 = inv_mix_single_col([x2[8], x2[9], x2[10], x2[11]])
                                    if B2[0] != (SBOX[base1[8] ^ K8] ^ K11):
                                        continue
                                    if B2[1] != (SBOX[base1[13] ^ K13] ^ K10):
                                        continue
                                    if B2[2] != (SBOX[base1[2] ^ K2] ^ K2):
                                        continue
                                    if B2[3] != (SBOX[base1[7] ^ K7] ^ K1):
                                        continue

                                    K[2] = K2
                                    key = bytes(K)
                                    out, st = encrypt_block(P, key, states=True)
                                    if out == C and all(leak_ok(leak, r, st[r]) for r in range(8)):
                                        candidates.append(key)

    if len(candidates) != 1:
        raise RuntimeError(f'expected a unique key, got {len(candidates)} candidates: {[k.hex() for k in candidates]}')
    return candidates[0]


def main() -> None:
    base = Path(__file__).resolve().parent
    pt = (base / 'plaintext.bin').read_bytes()
    ct = (base / 'ciphertext.bin').read_bytes()
    leak = read_leak(base / 'leaked.txt')

    key = recover_key(pt, ct, leak)
    print(f'master key = {key.hex()}')

    n = len(pt) // 16
    for i in range(n):
        if encrypt_block(pt[16*i:16*i+16], key) != ct[16*i:16*i+16]:
            raise RuntimeError(f'verification failed at block {i}')
    print(f'verified {n}/{n} plaintext-ciphertext pairs')


if __name__ == '__main__':
    main()
