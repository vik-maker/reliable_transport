import sys, socket, time
from utils import PacketHeader, compute_checksum

ip, port, W = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
addr = (ip, port)
CHUNK = 1456      # 1472 - 16 byte header
TIMEOUT = 0.5     # 500 ms


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


def recv_ack(s, deadline):
    """Chờ ACK đến hạn deadline. Hết giờ thì trả về None."""
    while True:
        left = deadline - time.time()
        if left <= 0:
            return None
        s.settimeout(left)
        try:
            raw, _ = s.recvfrom(2048)
        except socket.timeout:
            return None
        h, _, ok = parse(raw)
        if ok and h.type == 3:     # chỉ nhận ACK đúng checksum
            return h


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

msg = sys.stdin.buffer.read()
chunks = [msg[i:i + CHUNK] for i in range(0, len(msg), CHUNK)]
total = len(chunks)
pkts = [None] + [make_pkt(2, i + 1, c) for i, c in enumerate(chunks)]

s.sendto(make_pkt(0, 0), addr)
while recv_ack(s, time.time() + TIMEOUT) is None:
    s.sendto(make_pkt(0, 0), addr)

base, nxt = 1, 1                      
deadline = time.time() + TIMEOUT
while base <= total:
    while nxt < base + W and nxt <= total:     
        s.sendto(pkts[nxt], addr)
        nxt += 1
    h = recv_ack(s, deadline)
    if h is None:                              
        for i in range(base, nxt):
            s.sendto(pkts[i], addr)
        deadline = time.time() + TIMEOUT
    elif h.seq_num > base:                     
        base = min(h.seq_num, total + 1)
        deadline = time.time() + TIMEOUT

s.sendto(make_pkt(1, total + 1), addr)
recv_ack(s, time.time() + TIMEOUT)
