import socket

host = "windy-catfish-32309.j77.aws-ap-south-1.cockroachlabs.cloud"
port = 26257

print(f"Testing DNS lookup for {host}...")
try:
    ip = socket.gethostbyname(host)
    print(f"[DNS SUCCESS] {host} resolves to {ip}")
    
    print(f"Testing TCP connection to {ip}:{port}...")
    s = socket.create_connection((ip, port), timeout=5)
    print(f"[TCP SUCCESS] Connected to CockroachDB Cloud port {port}")
    s.close()
except Exception as e:
    print(f"[NETWORK ERROR] {e}")
