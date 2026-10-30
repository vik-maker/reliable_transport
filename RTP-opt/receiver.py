import sys, socket
from utils import PacketHeader, compute_checksum

ip, port, W = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])


def make_pkt(t, seq, data=b""):
    h = PacketHeader(type=t, seq_num=seq, length=len(data))
    h.checksum = compute_checksum(h / data)
    return bytes(h / data)


def parse(raw):
    h = PacketHeader(raw[:16])
    data = raw[16:16 + h.length]
    c = h.checksum
    h2 = PacketHeader(type=h.type, seq_num=h.seq_num, length=h.length, checksum=0)
    return h, data, compute_checksum(h2 / data) == c


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((ip, port))
out = sys.stdout.buffer

expected = None     
buf = {}            

while True:
    raw, addr = s.recvfrom(2048)
    h, data, ok = parse(raw)
    if not ok:                         
        continue

    if h.type == 0:                     
        if expected is None:            
            expected = 1
        if expected == 1:               
            s.sendto(make_pkt(3, 1), addr)
        

    elif expected is None:
        continue

    elif h.type == 2:                   
        if h.seq_num >= expected + W:   
            continue
        if h.seq_num >= expected:
            buf[h.seq_num] = data
        while expected in buf:         
            out.write(buf.pop(expected))
            expected += 1
        s.sendto(make_pkt(3, h.seq_num), addr)  

    elif h.type == 1 and h.seq_num == expected:  
        s.sendto(make_pkt(3, h.seq_num), addr)
        break

out.flush()
