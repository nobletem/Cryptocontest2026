from assist import *

n = 64
q =  0x7f52f24e1b74ca8d80713d
t = 0x78eb84ea7c66913db445
#gcd(t,q) = 257
    
P.<x> = PolynomialRing(Zmod(257))
R.<z> = P.quotient(x^n + 1)

def coeffs64(poly):
    # Lift from R = F_p[x]/(x^n+1) to degree < n polynomial and pad coefficients.
    cs = list(poly.lift().coefficients(sparse=False))
    cs += [0] * (n - len(cs))
    return [Integer(c) for c in cs[:n]]

c0_1,c1_1 = get_cipher('ctxt_day1.txt',1)
c0_2,c1_2 = get_cipher('ctxt_day2.txt',2)

c0_1 = vector(Zmod(q),c0_1)
c0_2 = vector(Zmod(q),c0_2)
c1_1 = vector(Zmod(q),c1_1)
c1_2 = vector(Zmod(q),c1_2)

del_c1 = c1_2 - c1_1
del_c0 = c0_2 - c0_1

del_c1 = del_c1.change_ring(Zmod(257))
del_c0 = del_c0.change_ring(Zmod(257))
B = matrix(Zmod(257),64,64)

for i in range(64):
    tmp_m = -1*del_c0[:i:-1]
    tmp = del_c0[:1+i][::-1]
    tmp = tmp.concatenate(tmp_m)
    B[i] = tmp


del_m = [0]*n
del_m[n-1] = 1
del_m = vector(Zmod(257),del_m)
s = B.solve_right(del_c1 - del_m)
s = signed(s)
print("[+] secret key : ",s)

s = R(s)
c0_1 = R(c0_1.list())
c0_2 = R(c0_2.list())
c1_1 = R(c1_1.list())
c1_2 = R(c1_2.list())

state_report_1 = coeffs64(c1_1 - (c0_1*s))
state_report_2 = coeffs64(c1_2 - (c0_2*s))
print("[+] state_report_1 : ",state_report_1)
print("[+] state_report_2 : ",state_report_2)

state_report_1 = ''.join(chr(x) for x in state_report_1)
state_report_2 = ''.join(chr(x) for x in state_report_2)

print("[+] state_report_1 : ",state_report_1)
print("[+] state_report_2 : ",state_report_2)




