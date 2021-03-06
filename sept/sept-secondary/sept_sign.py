#!/usr/bin/env python
import sys
from struct import pack as pk, unpack as up
from Crypto.Cipher import AES
from Crypto.Hash import CMAC
import KEYS

def shift_left_xor_rb(s):
    N = int(s.encode('hex'), 16)
    if N & (1 << 127):
        N = ((N << 1) ^ 0x87) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
    else:
        N = ((N << 1) ^ 0x00) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
    return ('%032x' % N).decode('hex')

def sxor(x, y):
    return ''.join(chr(ord(a) ^ ord(b)) for a,b in zip(x, y))
    
def get_last_block_for_desired_mac(key, data, desired_mac):
    assert len(desired_mac) == 0x10
    k1 = shift_left_xor_rb(AES.new(key, AES.MODE_ECB).encrypt('\x00'*0x10))
    if len(data) & 0xF:
        k1 = shift_left_xor_rb(k1)
        data += '\x80'
        data += '\x00' * ((0x10 - (len(data) & 0xF)) & 0xF)
    num_blocks = (len(data) + 0xF) >> 4
    last_block = sxor(AES.new(key, AES.MODE_ECB).decrypt(desired_mac), k1)
    if len(data) > 0x0:
        last_block = sxor(last_block, AES.new(key, AES.MODE_CBC, '\x00'*0x10).encrypt(data)[-0x10:])
    return last_block

def sign_encrypt_code(code, sig_key, enc_key, iv, desired_mac):
    # Pad with 0x20 of zeroes.
    code += '\x00' * 0x20
    code_len = len(code)
    code_len += 0xFFF
    code_len &= ~0xFFF
    code += '\x00' * (code_len - len(code))
    
    # Add empty trustzone, warmboot segments.
    code += '\x00'* (0x1FE0 - 0x10)
    pk11_hdr = 'PK11' + pk('<IIIIIII', 0x1000, 0, 0, code_len - 0x20, 0, 0x1000, 0)
    pk11 = pk11_hdr + code
    enc_pk11 = AES.new(enc_key, AES.MODE_CBC, iv).encrypt(pk11)
    enc_pk11 = pk('<IIII', len(pk11) + 0x10, 0, 0, 0) + iv + enc_pk11
    enc_pk11 += get_last_block_for_desired_mac(sig_key, enc_pk11, desired_mac)
    enc_pk11 += CMAC.new(sig_key, enc_pk11, AES).digest()
    return enc_pk11
    
def main(argc, argv):
    if argc != 3:
        print('Usage: %s input output' % argv[0])
        return 1
    with open(argv[1], 'rb') as f:
        code = f.read()
    assert (len(code) & 0xF) == 0
    # TODO: Support dev unit crypto
    with open(argv[2], 'wb') as f:
        f.write(sign_encrypt_code(code, KEYS.HOVI_SIG_KEY_PRD, KEYS.HOVI_ENC_KEY_PRD, KEYS.IV, 'THANKS_NVIDIA_<3'))
    return 0
        
if __name__ == '__main__':
    sys.exit(main(len(sys.argv), sys.argv))