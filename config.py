from utils import *

bindings = [
    {
        "sequence": [mod("leftmeta"), "enter"],
        "action": lambda: run_cmd('wezterm'),
    },
    {
        "sequence": [mod("leftmeta"), mod("leftshift"), "enter"],
        "action": lambda: run_cmd('wezterm connect mahmooz2'),
    },
    # {
    #     "sequence": [mod("leftmeta"), "x", "c", "1"],
    #     "action": lambda: print('reached 1'),
    # },
    {
        "sequence": ["mod(leftmeta)", "r"],
        "action": lambda: run_cmd('run.sh'),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "k"],
        "action": lambda: (print('kill process'), run_cmd('kill_process.sh')),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "w"],
        "action": lambda: run_cmd('firefox'),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "e"],
        "action": lambda: run_cmd('emacs'),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "b"],
        "action": lambda: run_cmd('web_bookmarks.sh'),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "o"],
        "action": lambda: run_cmd('terminal_with_cmd.sh top'),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "p"],
        "action": lambda: run_cmd('terminal_with_cmd.sh pulsemixer'),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "i"],
        # "action": lambda: run_cmd('cd ~/data/images/scrots/; ls -t | sxiv -i'),
        # "action": lambda: run_cmd('cd ~/data/images/scrots/; ls -t --color=no | xargs imv'),
        "action": lambda: subprocess.Popen(
            f"su mahmooz -c 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus WAYLAND_DISPLAY=wayland-1 GDK_BACKEND=wayland XDG_RUNTIME_DIR=/run/user/1000 sh -c \"cd ~/data/images/scrots/; ls -t --color=no | xargs imv\"'",
            shell=True,
            start_new_session=True
        )
    },
    {
        "sequence": ["mod(leftmeta)", "x", "a"],
        "action": lambda: run_cmd(""" HYPRLAND_INSTANCE_SIGNATURE=$(hyprctl instances | head -1 | cut -d " " -f2 | tr -d ":") sh -c "cd ~/work/widgets; nix-shell --run \\"python bar.py\\"" """),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "t"],
        "action": [mod("leftctrl"), "c", "h", "e", "l", "l", "o"],
    },
    {
        "sequence": [mod("leftmeta"), "x", "c"],
        "action": lambda: run_cmd('code'),
    },
    {
        "sequence": [mod("leftmeta"), "x", "x"],
        "action": lambda: run_cmd('xournalpp'),
    },
    {
        "sequence": [mod("leftmeta"), "p"],
        "action": lambda: run_cmd('myscrot.sh'),
    },
    {
        "sequence": [mod("leftmeta"), mod("leftshift"), "p"],
        "action": lambda: run_cmd('myscrot.sh 1'),
    },
    {
        "sequence": [mod("leftmeta"), "x", "j"],
        "action": lambda: run_cmd('jellyfinmediaplayer'),
    },
    {
        "sequence": [mod("leftmeta"), "x", "l"],
        "action": lambda: run_cmd('lem'),
    },

    # reload keybindings from config.py
    {
        "sequence": ["mod(leftmeta)", "x", "r"],
        "action": "reload",
    },

    {
        "sequence": ["rightshift"],
        "action": [mod("leftctrl"), "space"],
    },
]

# check evdev.ecodes.ecodes for all options, we ommit KEY_ and downcase
# also evdev.ecodes.KEY
remaps = [
    {
        "src": 'capslock',
        "dest": 'esc',
    },
    {
        "src": 'rightalt',
        "dest": 'leftctrl',
    },
]