import os
import socket
import sys
import threading

SOCK_FILE = '/tmp/keys.py.sock'

def client(message):
    if not os.path.exists(SOCK_FILE):
        print(f"File {SOCK_FILE} doesn't exists")
        sys.exit(-1)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK_FILE)

    s.sendall(message.encode())

    data = s.recv(1024)
    print(f'Received bytes: {repr(data)}')

def server():
    if os.path.exists(SOCK_FILE):
        os.remove(SOCK_FILE)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(SOCK_FILE)
    s.listen(0)

    while True:
        conn, addr = s.accept()
        print('Connection by client')
        all = []
        while True:
            data = conn.recv(1024)
            if not data:
                break
            all.append(data)
        print(all)

def start_server():
    thread = threading.Thread(target=server, args=())
    thread.daemon = True
    thread.start()