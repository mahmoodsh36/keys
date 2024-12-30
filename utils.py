import subprocess

from os import listdir
from os.path import join

def run_cmd(cmd):
    subprocess.Popen(
        f"su mahmooz -c 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus WAYLAND_DISPLAY=wayland-1 GDK_BACKEND=wayland XDG_RUNTIME_DIR=/run/user/1000 {cmd}'",
        shell=True,
        start_new_session=True
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