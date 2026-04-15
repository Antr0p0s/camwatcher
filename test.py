import socket

DAQ_IP   = "192.168.0.101"
PORT     = 54211

print("[1] Testing UDP discovery broadcast...")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.settimeout(2.0)
s.bind(('', 0))
s.sendto(b'D', ('<broadcast>', PORT))
try:
    data, addr = s.recvfrom(1024)
    print(f"    Got reply from {addr}: {data.hex()}")
except socket.timeout:
    print("    No broadcast reply (device not responding to discovery)")
s.close()

print("\n[2] Testing UDP connect handshake directly to device IP...")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2.0)
msg = bytearray(5)
msg[0] = ord('C')   # connect code message
# bytes 1-4 = connect code = 0
s.sendto(msg, (DAQ_IP, PORT))
try:
    data, addr = s.recvfrom(10)
    print(f"    Got reply: {data.hex()}")
    print(f"    Reply byte[0]={chr(data[0])!r}  byte[1]={hex(data[1])}")
except socket.timeout:
    print("    No reply to connect message (device not responding on UDP)")
s.close()

print("\n[3] Testing raw TCP connect...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3.0)
try:
    s.connect((DAQ_IP, PORT))
    print("    TCP connect succeeded!")
    s.close()
except ConnectionRefusedError:
    print("    TCP refused (expected if UDP handshake must come first)")
except socket.timeout:
    print("    TCP timed out (firewall dropping packets?)")
except Exception as e:
    print(f"    TCP error: {e}")
