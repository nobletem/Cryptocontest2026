# https://rump2007.cr.yp.to/15-shumow.pdf
import csv

p = Integer(0xd9047b5f32dda5ca6f569b)
a = Integer(0x674fdf5b55923897a16f40)
b = Integer(0x1d0c9956783f6026e6c981)
n = Integer(0x2b674bdfd6fc4ba4ba751d)

Px = Integer(0x5340e87bd80d1463a6ff8d)
Py = Integer(0x94ebeb5ca5b3c685e00c20)
Qx = Integer(0x4a05101411039decf537a5)
Qy = Integer(0x3395a009c2210836b63d4b)

r0 = Integer(0xb3939f4aadcc13ca74)
r1 = Integer(0x617985fad38ec3b1a3)
r2 = Integer(0xd8c20715ccc94d2283)
rs = [r0, r1, r2]

Fp = GF(p)
E = EllipticCurve(Fp, [a, b])  # y^2 = x^3 + a*x + b
P = E(Fp(Px), Fp(Py))
Q = E(Fp(Qx), Fp(Qy))

assert n * P == E(0)
assert n * Q == E(0)

# ----------------------------------------------------------------------
# 1. Recover backdoor scalar d from telemetry.csv.
#    Model: summary = ((scale*d + offset) mod n) >> 20.
# ----------------------------------------------------------------------
rows = []
with open('telemetry.csv', newline='') as f:
    for row in csv.DictReader(f):
        rows.append({
            'round': int(row['round']),
            'scale': Integer(int(row['scale'], 16)),
            'offset': Integer(int(row['offset'], 16)),
            'summary': Integer(int(row['summary'], 16)),
        })

B = Integer(1) << 20
rA, rB = rows[0], rows[1]
inv_scale0 = inverse_mod(rA['scale'], n)

d_candidates = []
for e0 in range(B):
    d = ((rA['summary'] * B + e0 - rA['offset']) * inv_scale0) % n
    if all((((rr['scale'] * d + rr['offset']) % n) >> 20) == rr['summary'] for rr in rows):
        print('[+] e0 : ',e0)
        d_candidates.append(Integer(d))

assert len(d_candidates) == 1
backdoor_d = d_candidates[0]
assert backdoor_d * Q == P

print('[+] d =', hex(backdoor_d))

# ----------------------------------------------------------------------
# 2. Predict r3 using the Dual_EC backdoor.
#    Given r_i, enumerate 16 missing low bits of X(s_{i+1} Q).
#    If R = s_{i+1}Q, then dR = s_{i+1}P, so X(dR) = s_{i+2}.
# ----------------------------------------------------------------------
TRUNC = 16

def tmsb(x):
    return Integer(x) >> TRUNC

def lifted_points_from_truncated_output(r):
    base = Integer(r) << TRUNC
    for low in range(1 << TRUNC):
        x = base + low
        if x >= p:
            continue
        try:
            for R in E.lift_x(Fp(x), all=True):
                yield Integer(x), R
        except ValueError:
            pass

stage1 = set([])
for x0, R0 in lifted_points_from_truncated_output(r0):
    s2 = Integer((backdoor_d * R0)[0])
    x1 = Integer((s2 * Q)[0])
    if tmsb(x1) == r1:
        stage1.add((s2, x0, x1))

print('[+] stage1 : ',stage1)
stage2 = set([])
for s2, x0, x1 in stage1:
    s3 = Integer((s2 * P)[0])
    x2 = Integer((s3 * Q)[0])
    if tmsb(x2) == r2:
        stage2.add((s2, s3, x0, x1, x2))

print('[+] stage2 : ',stage2)

s2, s3, x0_full, x1_full, x2_full = list(stage2)[0]
s4 = Integer((s3 * P)[0])
x3_full = Integer((s4 * Q)[0])
r3 = tmsb(x3_full)
print('s2 : ',hex(s2))
print('s3 : ',hex(s3))
print('s4 : ',hex(s4))
print('x0 =', hex(x0_full))
print('x1 =', hex(x1_full))
print('x2 =', hex(x2_full))
print('x3 =', hex(x3_full))
print('r3 =', hex(r3))
