import subprocess
import os
from os import listdir
from os.path import join
import pwd

# should work better but i need to fix some behavior (theming, PATH, etc..)
def run_cmd2(cmd, username='mahmooz'):
    try:
        # get target user details
        user_info = pwd.getpwnam(username)
        user_uid = user_info.pw_uid
        user_home = user_info.pw_dir
        # determine XDG_RUNTIME_DIR
        xdg_runtime_dir = f"/run/user/{user_uid}"
        # find the latest wayland display socket
        wayland_dir = f"{xdg_runtime_dir}/wayland-"
        wayland_files = [f for f in os.listdir(xdg_runtime_dir) if f.startswith("wayland-")]

        if not wayland_files:
            print(f"no Wayland display found for user {username}.")
            return None

        # sort by modification time (newest first)
        wayland_files.sort(key=lambda x: os.path.getmtime(os.path.join(xdg_runtime_dir, x)), reverse=True)
        wayland_display = wayland_files[0]

        # build environment variables
        env = {
            "DBUS_SESSION_BUS_ADDRESS": f"unix:path={xdg_runtime_dir}/bus",
            "WAYLAND_DISPLAY": wayland_display,
            "GDK_BACKEND": "wayland",
            "XDG_RUNTIME_DIR": xdg_runtime_dir,
            "HOME": user_home,
            "PATH": "/run/current-system/sw/bin/:/home/mahmooz/.local/bin/",
            "WORK_DIR": '/home/mahmooz/work/'
        }

        # prepare the command
        full_cmd = ["sh", "-c", cmd]

        # debug: print what's being executed
        print(f"running command as {username}:")
        print(f"  command: {' '.join(full_cmd)}")
        print(f"  env: {env}")

        # start the process
        process = subprocess.Popen(
            full_cmd,
            env=env,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            text=True,
            user=username,
            start_new_session=True
        )
    except Exception as e:
        print(f"exception: {e}")
        return None

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
            ['sudo', '-u', username, 'dash', '-lc',
             'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus WAYLAND_DISPLAY=$(basename $(ls -t /run/user/$(id -u)/wayland* | head -1)) GDK_BACKEND=wayland XDG_RUNTIME_DIR=/run/user/1000 ' + cmd],
            # stdout=dn, stderr=dn, stdin=dn,
            start_new_session=True,
            # close_fds=True,
            # env=env,
            # shell=True,
            # user=username,
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
