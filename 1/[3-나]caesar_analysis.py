import string

alphabet = string.ascii_uppercase
freq = [
    8.17, 1.50, 2.78, 4.25, 12.70, 2.23, 2.02,
    6.09, 6.97, 0.15, 0.77, 4.03, 2.41, 6.75,
    7.51, 1.93, 0.10, 5.99, 6.33, 9.06, 2.76,
    0.98, 2.36, 0.15, 1.97, 0.07
]
freq_c = [
    428, 181, 134, 45, 355, 57, 1676,
    459, 751, 734, 2524, 495, 245, 899,
    1484, 37, 36, 1016, 499, 1427, 1479,
    444, 28, 1198, 1361, 1905
]
total = sum(freq_c)
freq_n = [
    total * percentage / 100
    for percentage in freq
]
results = []


def rotlist(values, count):
    count %= len(values)
    return values[count:] + values[:count]


def chi_square(observed, expected):
    return sum(
        (observed_count - expected_count) ** 2 / expected_count
        for observed_count, expected_count in zip(observed, expected)
    )


for key in range(26):
    freq_r = rotlist(freq_c, key)
    score = chi_square(freq_r, freq_n)
    results.append((key, score))
    print(f"Key {key:2d}: chi-square = {score:.3f}")

best_key, best_score = min(results, key=lambda result: result[1])

print()
print(f"관측 문자 수: {total}")
print(f"추정 복호화 키: {best_key}")
print(f"추정 이동 문자: {alphabet[best_key]}")
print(f"최소 카이제곱 값: {best_score}")
