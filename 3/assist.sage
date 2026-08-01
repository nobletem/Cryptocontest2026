from Crypto.Util.number import long_to_bytes, bytes_to_long

def xor(x,y):
    return bytes(a ^^ b for a, b in zip(x, y))

def bitrev128(n):
    r = 0
    for i in range(128):
        if (n >> i) & 1:
            r |= 1 << (127 - i)
    return r

def block2K(block: bytes):
    n = bitrev128(bytes_to_long(block))
    bits = [(n >> i) & 1 for i in range(128)]
    return from_V(vector(GF(2), bits))          # 비트벡터 -> 필드원소

def K2block(elt):
    bits = to_V(elt)                             # 필드원소 -> 비트벡터
    n = 0
    for i in range(128):
        if bits[i] == 1:
            n |= (1 << i)
    return long_to_bytes(bitrev128(n), 16)

def pad16(b):
    return b if len(b) % 16 == 0 else b + b'\x00' * (16 - len(b) % 16)

def ghash_blocks(aad: bytes, ct: bytes):
    data = pad16(aad) + pad16(ct)
    data += (len(aad)*8).to_bytes(8,'big') + (len(ct)*8).to_bytes(8,'big')
    return [block2K(data[i:i+16]) for i in range(0, len(data), 16)]   

def diff_poly(aad1, ct1, tag1, aad2, ct2, tag2):
    b1 = ghash_blocks(aad1, ct1)
    b2 = ghash_blocks(aad2, ct2)

    n = max(len(b1), len(b2))
    b1 = [K(0)]*(n-len(b1)) + b1
    b2 = [K(0)]*(n-len(b2)) + b2
    diffs = [u + v for u, v in zip(b1, b2)]     # GF(2)라 +와 XOR 동일
    poly = R(block2K(xor(tag1, tag2)))          # 상수항 (z^0)
    for i in range(n):
        poly += diffs[i] * z^(n - i)
    return poly

