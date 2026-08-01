#!/usr/bin/env python3

from __future__ import annotations

import argparse
import logging
import re
import signal
import sys
import time
from pathlib import Path
from typing import Iterable, Mapping, Optional
from sage.all import ZZ, gcd, inverse_mod, var
import cuso


def hx(text: str) -> int:
    return int("".join(text.split()), 16)


# ---------------------------------------------------------------------------
# 문제 상수
# ---------------------------------------------------------------------------

P_BITS = 1024
ALL_P_BITS = (1 << P_BITS) - 1

MASK = hx(
    """
    ffffffffffffffff fffffffff0ffffff ffffffffffffffff c00000000000fffe
    0000000000000000 000003ffe0000000 0000000000ffffff ffffffffffffffff
    ffffffffffffffff fffffff000000000 000003ffe0000000 00000000000001ff
    ffffffffffffffff fffffffffc3fffff ffffffffffffffff ffffffffffffffff
    """
)

P_LEAK = hx(
    """
    ffa360d46885c534 d186538170633faf c2c0548a2e24a2c1 c0000000000039e2
    0000000000000000 000000a520000000 00000000003e2de4 c436d2ca740a6246
    99e1a1af94045c63 261323c000000000 000003bba0000000 00000000000000e5
    0b0bc2461fcbac07 26360c2c0809450a 9a892cbf1d98ceee 48827591ccc593c9
    """
)

N = hx(
    """
    e505004fb5d34eb7 12d48ff4bbe8d27f c388133c6c0e7340 01061c0ee0a4edc6
    37c04fe8dd376185 de8ba04d0ccdbabb 93ab7c371b88d92e 865eec42b028c61d
    d7004ebf2ebb5d69 d0a09142be5c9de4 da16e514eea31817 2ecda6cd192073eb
    afb1e02d522ec053 34590ea6d75960c4 937bf64f9700db17 7a4aa3da6aae6807
    e5e32c0d0e428a0d b68d299f20c235d8 4ef459b0cf118286 59c31663c9ea8204
    4b28152c89a9c36c 3ec4303bd36664fd 77fb02c58340bdae 21120326d83fc017
    34bc90048dec9fe3 5f08c8fdc523abf8 4a91ec430f495672 37c3153a2035ff62
    5613b6dc3e6cb14d 50e18b8a79b25d67 8465b3ad02f5b7d8 18a1e2d635a0baf1
    """
)

E = 0x10001

CT = hx(
    """
    8919342826ef3821 5af31e00c9290c4c 50ef9ff9e1afc591 47fab5b096361035
    e85f5fc95b73b069 7813b57b831a807d 41bcbecde5b9e663 9e2845b14e395ed0
    e5d995e63709ac0c 5ee2337228ee76bc bad857b14904aa2e 8e9997671908a634
    d0d1dda1d062ce7f 2e3293ddec8f5cce 26029292d594a062 dcf317d2a8380f43
    d72551889efceb87 6c8945a50382272e 76ed6b6fcdff1603 44e9e948e2b6e740
    e78bedf25f30e2c7 eeb5f74686c8eadc 29cea04ff08cfd86 dfd3d2a1632bf04a
    d5cfa369892a2da4 0f0dc0098ce6b731 d841aab3d0c8b78e b69c4625c47c4ad7
    158d49bb5d879581 e02bc525abe47f39 f699864bc5ce1de7 19430dae7aa5480b
    """
)

LOW_GUESS = (150, 4)
HIGH_GUESS = (920, 4)
BLOCKS = ((265, 155), (600, 230))


def block_mask(start: int, width: int) -> int:
    return ((1 << width) - 1) << start


GUESS_MASK = block_mask(*LOW_GUESS) | block_mask(*HIGH_GUESS)
MERGED_UNKNOWN_MASK = block_mask(*BLOCKS[0]) | block_mask(*BLOCKS[1])


# ---------------------------------------------------------------------------
# 조기 스킵(EARLY ABORT) 로직
# ---------------------------------------------------------------------------


class GuessRejected(Exception):
    """cuso 로그 패턴 또는 timeout 으로부터 '이 guess는 오답'이라고 조기 판정됨."""


_ATTEMPT_MSG = "Attempting the automated multivariate Coppersmith method"
_MULT_RE = re.compile(r"multiplicity (\d+)")


class EarlyAbortFilter(logging.Filter):
    """cuso가 뿜어내는 로그를 관찰하다가 '재시도(=오답 조짐)'가 보이면
    즉시 GuessRejected를 던져서 cuso 실행 중간에 강제로 빠져나온다.

    - attempt_count 가 max_attempts 를 넘으면: "Attempting the automated
      multivariate Coppersmith method" 가 반복 = multiplicity를 올려서
      다시 시도하는 중 = 정답이 아닐 가능성이 높다고 보고 중단.
    - multiplicity 가 max_multiplicity 를 넘으면: 마찬가지로 중단.
    """

    def __init__(self, max_attempts: int, max_multiplicity: int):
        super().__init__()
        self.max_attempts = max_attempts
        self.max_multiplicity = max_multiplicity
        self.attempt_count = 0

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()

        if _ATTEMPT_MSG in msg:
            self.attempt_count += 1
            if self.attempt_count > self.max_attempts:
                raise GuessRejected(
                    f"'{_ATTEMPT_MSG}' 가 {self.attempt_count}번째 반복됨 "
                    f"(max_attempts={self.max_attempts}) -> 오답으로 판정"
                )

        m = _MULT_RE.search(msg)
        if m:
            multiplicity = int(m.group(1))
            if multiplicity > self.max_multiplicity:
                raise GuessRejected(
                    f"multiplicity={multiplicity} > "
                    f"max_multiplicity={self.max_multiplicity} -> 오답으로 판정"
                )

        return True  # 정상적으로 로그는 계속 출력되게 둔다


# ---------------------------------------------------------------------------
# 문제 구성 / 결과 검증
# ---------------------------------------------------------------------------


def value_by_name(root: Mapping, name: str) -> Optional[int]:
    for key, value in root.items():
        if str(key) == name:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def build_problem(guess: int):
    low = guess & 0xF
    high = (guess >> 4) & 0xF
    guess_bits = (low << LOW_GUESS[0]) | (high << HIGH_GUESS[0])

    # 원본 leak에 두 nibble guess를 삽입한다.
    guessed_leak = (P_LEAK & ~GUESS_MASK) | guess_bits

    # 병합한 두 구간 안의 known-gap 비트까지 버린다.
    effective_mask = (MASK | GUESS_MASK) & ~MERGED_UNKNOWN_MASK & ALL_P_BITS
    p_base = guessed_leak & effective_mask

    y0, y1 = var("y0 y1")
    ys = (y0, y1)
    expression = ZZ(p_base)
    bounds = {}

    for y, (start, width) in zip(ys, BLOCKS):
        center = 1 << (width - 1)
        expression += ZZ(1 << start) * (y + center)
        bounds[y] = (-center - 1, center)

    p_min = max(1 << (P_BITS - 1), p_base)
    p_max = min(ALL_P_BITS, p_base | MERGED_UNKNOWN_MASK)

    assert 0 <= guess <= 0xFF
    assert (P_LEAK & ~MASK) == 0
    assert (MASK & GUESS_MASK) == 0
    assert ((MASK | GUESS_MASK) | MERGED_UNKNOWN_MASK) == ALL_P_BITS
    assert effective_mask == (ALL_P_BITS ^ MERGED_UNKNOWN_MASK)
    assert (p_base & MERGED_UNKNOWN_MASK) == 0

    return expression, ys, bounds, effective_mask, p_base, p_min - 1, p_max + 1


def candidate_factors(root: Mapping, expression, ys) -> Iterable[int]:
    values = []

    p_value = value_by_name(root, "p")
    if p_value is not None:
        values.append(p_value)

    substitutions = {}
    for y in ys:
        value = value_by_name(root, str(y))
        if value is None:
            substitutions = {}
            break
        substitutions[y] = ZZ(value)

    if substitutions:
        values.append(int(expression.subs(substitutions)))

    seen = set()
    for value in values:
        for candidate in (int(value), abs(int(value)), int(gcd(abs(int(value)), N))):
            if candidate not in seen:
                seen.add(candidate)
                yield candidate


def valid_factor(candidate: int, effective_mask: int, p_base: int) -> bool:
    return (1 < candidate < N and candidate.bit_length() == P_BITS and N % candidate == 0 and (candidate & effective_mask) == p_base)


def decrypt_and_save(p: int, output: Path) -> None:
    q = N // p
    phi = (p - 1) * (q - 1)
    d = int(inverse_mod(E, phi))
    m = pow(CT, d, N)
    plaintext = m.to_bytes(max(1, (m.bit_length() + 7) // 8), "big")

    output.write_bytes(plaintext)
    logging.info("SUCCESS")
    logging.info("p = 0x%x", p)
    logging.info("q = 0x%x", q)
    logging.info("plaintext hex   = %s", plaintext.hex())
    logging.info("plaintext bytes = %r", plaintext)
    logging.info("saved           = %s", output)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def auto_int(text: str) -> int:
    return int(text, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="8-bit guess / 2-variable cuso attack")
    parser.add_argument("--guess", type=auto_int, required=True, help="0..255 또는 0x00..0xff")
    parser.add_argument("--output", type=Path, required=True, help="성공 시 평문 저장 경로")
    parser.add_argument("--debug", action="store_true")

    # --- 조기 스킵 관련 옵션 ---
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=1,
        help=(
            "'Attempting the automated multivariate Coppersmith method' 로그가 "
            "이 횟수를 초과해서 반복되면 오답으로 보고 즉시 중단한다. "
            "기본값 1: 최초 시도 이후 재시도(multiplicity 상승)가 관측되면 바로 중단."
        ),
    )
    parser.add_argument(
        "--max-multiplicity",
        type=int,
        default=7,
        help="이 값보다 큰 multiplicity 시도가 로그에서 감지되면 오답으로 보고 즉시 중단 (기본값 5).",
    )
    parser.add_argument(
        "--allow-higher-multiplicity",
        action="store_true",
        help="multiplicity/재시도 제한을 걸지 않고 cuso가 끝까지 시도하게 둔다 (조기 스킵 비활성화).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="guess 하나당 최대 대기 시간(초). 로그 패턴이 안 잡혀도 이 시간이 지나면 강제로 중단한다. 0이면 비활성화 (기본값 0).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0 <= args.guess <= 0xFF:
        raise SystemExit("[!] --guess는 0..255 범위여야 합니다.")

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    low = args.guess & 0xF
    high = (args.guess >> 4) & 0xF
    logging.info(
        "guess=0x%02x: p[920:923]=0x%x, p[150:153]=0x%x",
        args.guess,
        high,
        low,
    )

    expression, ys, bounds, effective_mask, p_base, p_lower, p_upper = build_problem(
        args.guess
    )
    logging.info("blocks=%s, unknown bits=%d", BLOCKS, sum(w for _, w in BLOCKS))
    logging.info("p_base=0x%0256x", p_base)

    # --- 조기 스킵용 필터를 root logger의 핸들러에 부착 ---
    # (basicConfig가 만든 핸들러에 붙여야, cuso 쪽 named logger에서
    #  propagate 되어 오는 레코드까지 전부 관찰할 수 있다.)
    max_multiplicity = 10**9 if args.allow_higher_multiplicity else args.max_multiplicity
    max_attempts = 10**9 if args.allow_higher_multiplicity else args.max_attempts
    early_abort_filter = EarlyAbortFilter(
        max_attempts=max_attempts, max_multiplicity=max_multiplicity
    )

    root_logger = logging.getLogger()
    target_handler = root_logger.handlers[0] if root_logger.handlers else None
    if target_handler is not None:
        target_handler.addFilter(early_abort_filter)

    # --- 안전망: SIGALRM 기반 timeout ---
    def _on_timeout(signum, frame):  # noqa: ARG001
        raise GuessRejected(f"timeout({args.timeout}s) 초과 -> 오답으로 판정")

    have_alarm = args.timeout > 0 and hasattr(signal, "SIGALRM")
    if have_alarm:
        signal.signal(signal.SIGALRM, _on_timeout)
        signal.alarm(args.timeout)

    started = time.monotonic()

    try:
        roots = cuso.find_small_roots(
            relations=[expression],
            bounds=bounds,
            modulus="p",
            modulus_multiple=N,
            modulus_lower_bound=p_lower,
            modulus_upper_bound=p_upper,
            use_graph_optimization=True,
            use_intermediate_sizes=True,
            allow_partial_solutions=False,
        )
    except GuessRejected as exc:
        logging.info(
            "guess=0x%02x 조기 스킵 (elapsed=%.1fs): %s",
            args.guess,
            time.monotonic() - started,
            exc,
        )
        return 2
    finally:
        if have_alarm:
            signal.alarm(0)
        if target_handler is not None:
            target_handler.removeFilter(early_abort_filter)

    logging.info("cuso elapsed=%.1fs", time.monotonic() - started)
    for root in roots or []:
        logging.info("root=%s", root)
        for candidate in candidate_factors(root, expression, ys):
            if valid_factor(candidate, effective_mask, p_base):
                args.output.parent.mkdir(parents=True, exist_ok=True)
                decrypt_and_save(candidate, args.output)
                logging.info("winning guess=0x%02x (%d)", args.guess, args.guess)
                return 0

    logging.error("FAIL: 검증 가능한 factor를 찾지 못했습니다.")
    return 2


if __name__ == "__main__":
    sys.exit(main())