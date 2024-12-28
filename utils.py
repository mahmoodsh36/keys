import subprocess

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