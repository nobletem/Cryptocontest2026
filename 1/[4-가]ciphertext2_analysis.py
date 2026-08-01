def longest(filename):
    with open(filename, "r") as f:
        lines = f.readlines()

    lines = [line.strip() for line in lines]
    return max(lines, key=len)


def lps(text):
    table = [0] * len(text)
    length = 0
    i = 1

    while i < len(text):
        if text[i] == text[length]:
            length += 1
            table[i] = length
            i += 1
        elif length > 0:
            length = table[length - 1]
        else:
            i += 1

    return table


def long_patterns(text, count=5):
    patterns = set()

    for start in range(len(text)):
        suffix = text[start:]
        table = lps(suffix)

        for length in table:
            if length > 0:
                patterns.add(suffix[:length])

    patterns = sorted(patterns, key=lambda pattern: (-len(pattern), pattern))
    selected = []

    for pattern in patterns:
        if not any(pattern in longer for longer in selected):
            selected.append(pattern)

        if len(selected) == count:
            break

    return selected


def kmp(text, pattern):
    positions = []
    table = lps(pattern)
    i = 0
    j = 0

    while i < len(text):
        if text[i] == pattern[j]:
            i += 1
            j += 1

            if j == len(pattern):
                positions.append(i - j)
                j = table[j - 1]
        elif j > 0:
            j = table[j - 1]
        else:
            i += 1

    return positions


ciphertext = longest("ciphertexts2.txt")
patterns = long_patterns(ciphertext)

print(ciphertext)
print("Length:", len(ciphertext))

for rank, pattern in enumerate(patterns, 1):
    positions = kmp(ciphertext, pattern)
    gaps = [
        positions[i + 1] - positions[i]
        for i in range(len(positions) - 1)
    ]

    print()
    print(f"Rank {rank}")
    print("Pattern:", pattern)
    print("Pattern length:", len(pattern))
    print("Positions:", positions)
    print("Gaps:", gaps)
