#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

gcc -O3 -Wall -Wextra -mavx2 -o contest contest.c
./contest
