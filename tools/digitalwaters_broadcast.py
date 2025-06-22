import socket
import subprocess
import time
import os
import shutil
from datetime import datetime

UDP_PORT = 9876
TCP_PORT = 9877
BROADCAST_MESSAGE = b'digitalwaters:8000'
RESPONSE_WAIT_TIME = 5  # seconds to wait for responses
BASE_DIR = "/home/rpi/ww/images"
EXCLUDE_DIR = "_archive"
END_OF_FILE_MARKER = b'\n::end-of-file::\n'

def get_ip_address():
    try:
        ip = subprocess.check_output("hostname -I", shell=True).decode().strip().split()[0]
        return ip
    except Exception:
        return "unknown"

def get_rpi_id():
    try:
        return subprocess.check_output("hostname", shell=True).decode().strip()
    except Exception:
        return "unknown"

def get_all_files(base_dir):
    file_list = []
    for root, _, files in os.walk(base_dir):
        if EXCLUDE_DIR in os.path.relpath(root, base_dir).split(os.sep):
            continue
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, base_dir)
            file_list.append((relative_path, full_path))
    return file_list

def send_file(sock, relative_path, full_path):
    try:
        sock.sendall(relative_path.encode() + b'\n')
        with open(full_path, 'rb') as f:
            while chunk := f.read(4096):
                sock.sendall(chunk)
        sock.sendall(END_OF_FILE_MARKER)
        print(f"[✓] Sent {relative_path}")
    except Exception as e:
        print(f"[!] Failed to send {relative_path}: {e}")

def archive_sent_data():
    archive_path = os.path.join(BASE_DIR, EXCLUDE_DIR)
    os.makedirs(archive_path, exist_ok=True)

    for entry in os.listdir(BASE_DIR):
        if entry == EXCLUDE_DIR:
            continue
        source_path = os.path.join(BASE_DIR, entry)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest_path = os.path.join(archive_path, f"{entry}_{timestamp}")

        try:
            if os.path.isdir(source_path):
                shutil.move(source_path, dest_path)
            else:
                shutil.move(source_path, archive_path)
            print(f"[→] Moved {entry} to _archive")
        except Exception as e:
            print(f"[!] Error archiving {entry}: {e}")

def serve_command_over_tcp():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        server.bind(('', TCP_PORT))
        server.listen(1)
        print(f"[✓] Waiting for file sync on port {TCP_PORT}")
        server.settimeout(15)

        try:
            conn, addr = server.accept()
        except socket.timeout:
            print("[!] No incoming file transfer. Skipping.")
            return

        with conn:
            print(f"[+] TCP connected to {addr[0]}")
            try:
                command = b""
                while not command.endswith(b'\n'):
                    chunk = conn.recv(1)
                    if not chunk:
                        break
                    command += chunk
                command = command.decode().strip().upper()
                print(f"[>] Received command: {command}")
            except Exception as e:
                print(f"[!] Failed to read command: {e}")
                return

            if command == "SEND_FILES":
                files = get_all_files(BASE_DIR + "/2025-06-04")
                
                try:
                    # Send total file count
                    file_count = len(files)
                    conn.sendall(f"NUM_FILES:{file_count}\n".encode())
                    print(f"[→] Announced {file_count} files")

                    # Send each file
                    for rel_path, full_path in files:
                        send_file(conn, rel_path, full_path)

                    print("[✓] All files sent. Archiving...")
                    archive_sent_data()
                except Exception as e:
                    print(f"[!] Error during file transfer: {e}")

            else:
                conn.sendall(f"Unknown command: {command}\n".encode())

def get_status_report():
    folder = BASE_DIR
    total_size, file_count, dir_count = collect_folder_stats(folder)
    total_size_gb = total_size / (1024 ** 3)

    # Get free space
    stat = os.statvfs('/')
    free_space = stat.f_bavail * stat.f_frsize / (1024 ** 3)

    # Get OS version
    try:
        with open("/etc/os-release") as f:
            lines = f.readlines()
            os_version = next((line.split('=')[1].strip().strip('"') for line in lines if line.startswith("PRETTY_NAME=")), "Unknown")
    except:
        os_version = "Unknown"

    # Get app version from a static file
    try:
        with open(os.path.join(BASE_DIR, "version.txt")) as f:
            app_version = f.read().strip()
    except:
        app_version = "Unknown"

    report = f"""Image Space Used: {total_size_gb:.2f} GB
        Num Images Captured: {file_count}
        Num Days Worth of Data: {dir_count}
        Remaining SD Space: {free_space:.2f} GB
        RPi OS Version: {os_version}
        DW FVA Version: {app_version}
        """
    return report.encode()

def collect_folder_stats(path):
    total_size = 0
    file_count = 0
    dir_count = 0

    for root, dirs, files in os.walk(path):
        dir_count += len(dirs)
        for f in files:
            file_path = os.path.join(root, f)
            try:
                total_size += os.path.getsize(file_path)
                file_count += 1
            except Exception as e:
                print(f"[WARN] Skipped file: {file_path}, reason: {e}")
    return total_size, file_count, dir_count

def broadcast_presence():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.bind(('', UDP_PORT))

    while True:
        ip = get_ip_address()
        rpi_id = get_rpi_id()

        if ip != "unknown":
            udp_sock.sendto(BROADCAST_MESSAGE, ('<broadcast>', UDP_PORT))
            print("Broadcast sent.")

            udp_sock.settimeout(RESPONSE_WAIT_TIME)
            try:
                while True:
                    data, addr = udp_sock.recvfrom(1024)
                    message = data.decode().strip()
                    sender_ip = addr[0]

                    if message == "receiver-ready":
                        reply = f"rpi-id:{rpi_id},ip:{ip}".encode()
                        time.sleep(0.2)
                        udp_sock.sendto(reply, addr)
                        print(f"[+] Handshake with {sender_ip}")

                    elif message == "RESTART_COLLECTOR":
                        print(f"[↻] Restarting collector (requested by {sender_ip})")
                        subprocess.run(["sudo", "systemctl", "restart", "myscript.service"])

                    elif message == "REBOOT":
                        print(f"[↻] Rebooting system (requested by {sender_ip})")
                        subprocess.run(["sudo", "reboot"])

                    elif message == "GET_STATUS":
                        print(f"[*] Sending status to {sender_ip}")
                        udp_sock.sendto(get_status_report(), addr)

                    elif message == "SEND_FILES_REQUEST":
                        print(f"[⇄] Received SEND_FILES_REQUEST from {addr[0]}, starting TCP server")
                        udp_sock.sendto(b"READY_FOR_FILES", addr)
                        serve_command_over_tcp()  # this listens for TCP and serves files

            except socket.timeout:
                pass

        else:
            print("No IP detected. Skipping broadcast.")

        time.sleep(6)

if __name__ == "__main__":
    broadcast_presence()
