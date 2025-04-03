import subprocess
import os
from os import listdir
from os.path import join

def run_cmd(cmd):
    username = 'mahmooz'

    old_env = os.environ.copy()
    env = {}
    defaults = {
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        "WAYLAND_DISPLAY": "wayland-1",
        "GDK_BACKEND": "wayland",
        "XDG_RUNTIME_DIR": "/run/user/1000",
        "PATH": old_env['PATH']
    }
    for key, value in defaults.items():
        env.setdefault(key, value)

    with open(os.devnull, 'wb') as dn:
        subprocess.Popen(
            cmd,
            # stdout=dn, stderr=dn, stdin=dn,
            start_new_session=True,
            # close_fds=True,
            env=env,
            shell=True,
            user='mahmooz',
        )

def mod(key):
    """use key as modifier"""
    return f"mod({key})"

def ismod(key):
    """check if key is used as a modifier"""
    return key.startswith('mod(')

def unmod(key):
    """remove mod() from around a key"""
    if not ismod(key):
        return key
    return key[4:].split(')')[0]

def find_kbd():
    DEV_INPUT_PATH = '/dev/input/by-path/'
    for file in listdir(DEV_INPUT_PATH):
        if file.endswith('event-kbd'):
            return join(DEV_INPUT_PATH, file)
    return None