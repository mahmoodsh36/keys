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

def server(keyhandler):
    if os.path.exists(SOCK_FILE):
        os.remove(SOCK_FILE)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(SOCK_FILE)
    s.listen(0)

    while True:
        conn, addr = s.accept()
        all = []
        SIZE = 1024
        while True:
            data = conn.recv(1024)
            if not data:
                break
            all.append(data)
            if len(data) < SIZE:
                break
        msg = ''.join(item.decode() for item in all)
        if msg.startswith('writeseq'):
            seq = eval(msg[len("writeseq"):])
            keyhandler.writeseq(seq, through_handler=True)
        conn.send(b'ok')

def start_server(keyhandler):
    thread = threading.Thread(target=server, args=(keyhandler,))
    thread.daemon = True
    thread.start()