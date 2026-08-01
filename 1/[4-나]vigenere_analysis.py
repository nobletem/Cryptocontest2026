import string

upper = string.ascii_uppercase

freq = [
    8.17, 1.50, 2.78, 4.25, 12.70, 2.23, 2.02,
    6.09, 6.97, 0.15, 0.77, 4.03, 2.41, 6.75,
    7.51, 1.93, 0.10, 5.99, 6.33, 9.06, 2.76,
    0.98, 2.36, 0.15, 1.97, 0.07
]


def rotlist(values, count):
    count %= len(values)
    return values[count:] + values[:count]


def chi_square(observed, expected):
    return sum(
        (observed_count - expected_count) ** 2 / expected_count
        for observed_count, expected_count in zip(observed, expected)
    )


def find_key(text):
    freq_c = [text.count(c) for c in upper]
    total = len(text)
    freq_n = [total * percentage / 100 for percentage in freq]
    results = []

    for key in range(26):
        p = rotlist(freq_c, key)
        score = chi_square(p, freq_n)
        results.append((key, score))

    return min(results, key=lambda result: result[1])


with open("ciphertexts2.txt", "r") as f:
    lines = f.readlines()

idx1 = ""
idx2 = ""
idx3 = ""
idx4 = ""
idx5 = ""

for line in lines:
    text = "".join(c for c in line.upper() if c in upper)
    idx1 = idx1 + text[0::5]
    idx2 = idx2 + text[1::5]
    idx3 = idx3 + text[2::5]
    idx4 = idx4 + text[3::5]
    idx5 = idx5 + text[4::5]

groups = [idx1, idx2, idx3, idx4, idx5]
key_values = []

for number, text in enumerate(groups, 1):
    key, score = find_key(text)
    key_values.append(key)
    print(f"idx{number}: length = {len(text)}, key = {key}, letter = {upper[key]}, chi-square = {score:.3f}")

print("Key values:", key_values)
print("Key:", "".join(upper[key] for key in key_values))
