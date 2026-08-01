import string

upper = string.ascii_uppercase


def read_cipher(filename):
    with open(filename, "r") as f:
        return f.read().replace("\n", "").strip().upper()


def IC(text):
    N = len(text)
    if N < 2:
        return 0
    counts = [text.count(c) for c in upper]
    numerator = sum(n * (n - 1) for n in counts)
    denominator = N * (N - 1)
    return numerator / denominator


ciphertext1 = read_cipher("ciphertexts1.txt")
ciphertext2 = read_cipher("ciphertexts2.txt")

print(f"Ciphertext1 IC: {IC(ciphertext1):.3f}")
print(f"Ciphertext2 IC: {IC(ciphertext2):.3f}")
