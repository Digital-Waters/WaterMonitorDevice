# digitalwaters_broadcast.py

import socket
import subprocess
import time

def is_connected():
    try:
        ip = subprocess.check_output("hostname -I", shell=True).decode().strip()
        return ip != ""
    except Exception:
        return False

def broadcast_presence():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    message = b'digitalwaters:8000'

    while True:
        if is_connected():
            sock.sendto(message, ('<broadcast>', 9876))
            print("Broadcasting...")
        else:
            print("Not connected. Skipping broadcast.")
        time.sleep(5)

if __name__ == "__main__":
    broadcast_presence()
