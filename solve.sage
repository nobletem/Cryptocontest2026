load('assist.sage')

P.<x> = PolynomialRing(GF(2))
f = x^128 + x^7 + x^2 + x + 1
K.<a> = GF(2^128,modulus = f)
R.<z> = PolynomialRing(K)
V, from_V, to_V = K.vector_space(map=True)

App_data1 = long_to_bytes(0x9c269a9f29810ab0a99141d1d84c3df5b3c6e328f879f64b2bcd6561fe7fe19a73edad45cd0fb968f4f0035dd4f7202b87c66b7a2f2442f6d53f)
App_data2 = long_to_bytes(0x9c269a9f29810ab0a99141d1d84c3df4afcdf677d263f31a7a8f2c70ad62f69a72eaa943dd56e42cf9f1e436ba7d1eb5ee2efe9b65522edc686099935ebb98284af75a6253d1b5c10ec1)
App_data3 = long_to_bytes(0x9c269a9f29810ab0a99141d1d84c3df6bfdcdb7dec7cf30462db203fbc36a29772edbf159643b468f5f1e520e7341daee867a49665542cd9b0d6e0ac2be205621f7ea4a034519f95)

# 0 : Explict Nonve, 1 : Ciphertext, 2 : Tag
# 0th ct len : 34, 1th ct len : 50, 2th ct len : 48
Adp = [(App_data1[:8],App_data1[8:-16],App_data1[-16:]),(App_data2[:8],App_data2[8:-16],App_data2[-16:]),(App_data3[:8],App_data3[8:-16],App_data3[-16:])]

pt = b'action=set_salary&uid=0007&amt=0100&month=202603'
mask = xor(pt,Adp[2][1])

# ---- AAD 구성: seq_num || 0x17 || 0x0303 || len ----
seqs = [1, 2, 3]
aads = []
for i in range(3):
    ctlen = len(Adp[i][1])
    aads.append(seqs[i].to_bytes(8,'big') + bytes([0x17, 0x03, 0x03]) + ctlen.to_bytes(2,'big'))


# ---- H 값 구하기 : type(H) = bytes, 112332a84132bc0c5c23a61037723683 ----
P1 = diff_poly(aads[0], Adp[0][1], Adp[0][2], aads[1], Adp[1][1], Adp[1][2])
P2 = diff_poly(aads[0], Adp[0][1], Adp[0][2], aads[2], Adp[2][1], Adp[2][2])

g = gcd(P1, P2)
g = g / g.leading_coefficient()     # monic 정규화
#print(g.degree())                   # 1

H = g[0]                      # z + H_field 꼴 (char 2라 부호 무관)
H = K2block(H)                # type(H) = bytes
print('[+] Successfully Obtained H : ',H.hex())                # 112332a84132bc0c5c23a61037723683

print('P^(1) : ',xor(Adp[0][1],mask))
print('P^(2) : ',xor(Adp[1][1],mask))
print('Key_stream : ', mask.hex())
# ---- E_K(counter 0) 얻기 ---- #

# application_data 첫 번째 tag 생성, len(gb0) : 5
H = block2K(H)
gb = ghash_blocks(aads[0], Adp[0][1])
res = H*gb[0]
for i in range(1,5):
    res = (res + gb[i])*H
    
res = K2block(res)
Ecounter0 = xor(Adp[0][2],res)
print('[+] Successfully Obtained E_K(counter0) : ',Ecounter0.hex())
# ---- Test : E_K(counter 0)랑 H가 제대로 계산이 되었는지 ---- #

# ---- Test 1 : 3번째 Adp를 통해 Test | success ----
gb = ghash_blocks(aads[2], Adp[2][1])
res = H*gb[0]
for i in range(1,5):
    res = (res + gb[i])*H

expect = xor(K2block(res),Ecounter0)
print('\n[+] ==== Test 1 result ====')
print('[+] Result : ', expect == Adp[2][2])
print('[+] Test expect : ', expect)
print('[+] Test original : ', Adp[2][2])

# ---- Test 2 : 2번째 Adp를 통해 Test | success ----
gb = ghash_blocks(aads[1], Adp[1][1])
res = H*gb[0]
for i in range(1,6):
    res = (res + gb[i])*H

expect = xor(K2block(res),Ecounter0)
print('\n[+] ==== Test 2 result ====')
print('[+] Result : ', expect == Adp[1][2])
print('[+] Test expect : ', expect)
print('[+] Test original : ', Adp[1][2])

# 위조 Message 생성
forge_pt = b'action=set_salary&uid=0007&amt=0500&month=202603'
forge_ct = xor(forge_pt,mask)
gb = ghash_blocks(aads[2], forge_ct)
res = H*gb[0]
for i in range(1,5):
    res = (res + gb[i])*H

tag = xor(K2block(res),Ecounter0)
print('\n[+] ==== Final Result ====')
forge_message = bytes([0x17, 0x03, 0x03, 0x00, 0x48]) + Adp[0][0] + forge_ct + tag
print('[+] Forge_message_hex : ',forge_message.hex())

# 17030300489c269a9f29810ab0a99141d1d84c3df6bfdcdb7dec7cf30462db203fbc36a29772edbf159643b468f1f1e520e7341daee867a49665542cd9f01f5a9c906b73ba3e13bbfea0e98a18
# 17030300489c269a9f29810ab0a99141d1d84c3df6bfdcdb7dec7cf30462db203fbc36a29772edbf159643b468f1f1e520e7341daee867a49665542cd9f01f5a9c906b73ba3e13bbfea0e98a18