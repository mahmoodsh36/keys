import subprocess
import os
from os import listdir
from os.path import join

def run_cmd(cmd):
    username = 'mahmooz'

    # vars_to_inherit = [] # 'PATH'
    #
    # old_env = os.environ.copy()
    # # env = old_env
    # env = {}
    # defaults = {
    #     "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    #     "WAYLAND_DISPLAY": "wayland-1",
    #     "GDK_BACKEND": "wayland",
    #     "XDG_RUNTIME_DIR": "/run/user/1000",
    #     "XDG_DATA_HOME": f"/home/{username}/.local/share",
    #     "XDG_CACHE_HOME": f"/home/{username}/.cache",
    #     "XDG_CONFIG_HOME": f"/home/{username}/.config",
    #     "XDG_STATE_HOME": f"/home/{username}/.local/state",
    #     "USER": username,
    #     "HOME": f"/home/{username}",
    #     "PATH": f"{old_env['PATH']}:/home/{username}/.local/bin",
    # }
    # for key, value in defaults.items():
    #     env.setdefault(key, value)
    # for key in vars_to_inherit:
    #     env.setdefault(key, old_env[key])

    with open(os.devnull, 'wb') as dn:
        subprocess.Popen(
            ['sudo', 'su', username, '-c',
             'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus WAYLAND_DISPLAY=wayland-1 GDK_BACKEND=wayland XDG_RUNTIME_DIR=/run/user/1000 ' + cmd],
            # stdout=dn, stderr=dn, stdin=dn,
            start_new_session=True,
            # close_fds=True,
            # env=env,
            # shell=True,
            user=username,
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