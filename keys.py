import evdev
from evdev import UInput, ecodes as e
import subprocess

MAX_HIST_SIZE = 25

kbd_path = '/dev/input/event0'
try:
    kbd_path = subprocess.check_output("libinput_find_keyboard.sh", shell=True).decode().strip()
    print(f'got path {kbd_path}')
except:
    pass

# for injecting keys/events
ui = UInput()
# for capturing manual input
device = evdev.InputDevice(kbd_path)
print("Using device " + device.path + ' ' + device.name)

# key press history
history = []
active = []

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
    return "mod" in key

def unmod(key):
    """remove mod() from around a key"""
    if not ismod(key):
        return key
    return key[4:].split(')')[0]

bindings = [
    {
        "sequence": ["mod(leftmeta)", "enter"],
        "action": lambda: run_cmd('kitty'),
    },
    {
        "sequence": ["mod(leftmeta)", "x", "c", "1"],
        "action": lambda: print('reached 1'),
    },

    # programs/scripts
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
        "action": lambda: run_cmd('cd ~/data/images/scrots/; ls -t | sxiv -i'),
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

def normalize(code):
    """normalize the code of a key"""
    return code.lower().replace('key_', '')

def unnormalize(code):
    return f'KEY_{code.upper()}'

class MyKey:
    def __init__(self, keycode, scancode, keystate):
        self.keycode = keycode
        self.scancode = scancode
        self.keystate = keystate
        self.forwarded = True # whether to write it

    def is_held(self):
        return self.keystate != 'up'

    def code(self):
        return normalize(self.keycode)

class KeySequence():
    def __init__(self, sequence, action):
        self.progress_idx = 0 # index indiciating how many keys have been satisfied
        self.sequence = sequence
        self.action = action

    def left(self):
        return self.sequence[self.progress_idx:]

    def progress(self, key):
        """receive a key and decide how to progress, return whether the sequence
        should continue picking up keys or should terminate because it cant be
        satisfied.
        the return values are:
        0 for sequence not satisfied
        1 for sequence needs to continue receiving keys
        2 for sequence done"""
        # if the key isnt the one we're expecting we abort this sequence
        expected = self.left()[0]
        if ismod(expected):
            if key.code() != unmod(expected):
                satisfied = False
                for histkey in reversed(history):
                    if histkey.code() == unmod(expected) and histkey.is_held():
                        self.progress_idx += 1
                        satisfied = True
                        break
                if satisfied:
                    return self.progress(key)
                return 0
        elif key.code() != expected:
            return 0

        seq = self.left()
        # for i, seqkey in enumerate(seq):
        #     j = len(history) - len(seq) + i
        #     if len(history) >= len(seq):
        #         if ismod(seqkey):
        #             seqkey = unmod(seqkey)
        #             found_mod_in_hist = False
        #             for histkey in reversed(history):
        #                 if histkey.code() == seqkey:
        #                     print(histkey.keystate)
        #                     found_mod_in_hist = True
        #                     if not histkey.is_held():
        #                         print(8)
        #                         satisfied = False
        #                     break
        #             if not found_mod_in_hist:
        #                 print('8')
        #                 satisfied = False
        #         else:
        #             histkey = history[j]
        #             if histkey.code() != seqkey:
        #                 print(4)
        #                 satisfied = False
        #     else:
        #         print(3)
        #         satisfied = False
        # if satisfied:
        #     print('invoking ', seq)

        # if its not a modifier key, we check if it requires a modifier key
        # and if so we check whether that modifier key is still active (held)
        if not ismod(expected) and self.progress_idx > 0:
            i = 1
            prev = self.sequence[self.progress_idx - i]
            if ismod(prev):
                while ismod(prev) and i <= len(self.sequence):
                    for histkey in reversed(history):
                        if histkey.code() == unmod(prev):
                            if not histkey.is_held():
                                return 0
                            break
                    i += 1
                    prev = self.sequence[self.progress_idx - i]
            else:
                # if we have two normal keys in a row, then the second shouldnt have
                # any modifiers, here we check if any modifiers are held and if so
                # we discard this sequence
                for prev in self.sequence[:self.progress_idx]:
                    if ismod(prev):
                        for histkey in reversed(history):
                            if histkey.code() == unmod(prev):
                                if histkey.is_held():
                                    return 0
                                break
                key.forwarded = False

        self.progress_idx += 1

        # if we have reached the end of the sequence, execute the destined action
        # and return False to get the sequence removed.
        if self.progress_idx == len(self.sequence):
            self.action()
            return 2

        # return true to let this sequence continue progressing
        return 1

def handlekey(key):
    """main function that handles each key event"""
    global active
    global history

    keystate = key.keystate
    keycode = key.keycode
    scancode = key.scancode

    # handle key remapping
    code_towrite = scancode
    for remap in remaps:
        if normalize(keycode) == remap['src']:
            code_towrite = e.ecodes[unnormalize(remap['dest'])]

    towrite = True

    # handle key up
    if keystate == evdev.events.KeyEvent.key_up:
        # TODO: needs to be optimized
        for histkey in reversed(history):
            if histkey.keycode == keycode:
                histkey.keystate = "up"
                if not histkey.forwarded:
                    towrite = False
                break

    # handle key down
    if keystate == evdev.events.KeyEvent.key_hold:
        strstate = "hold"
        # TODO: needs to be optimized
        for histkey in reversed(history):
            if histkey.keycode == keycode:
                histkey.keystate = "hold"
                if not histkey.forwarded:
                    towrite = False
                break

    if keystate == evdev.events.KeyEvent.key_down:
        mykey = MyKey(keycode, scancode, "down")
        history.append(mykey)

        # exit unconditionally
        all = "".join([histkey.code() for histkey in history])
        if 'force4stop' in all:
            return False # exit

        # we need to keep track of the ones we just finished to avoid
        # S-r (or the likes) from being invoked twice
        done = []

        # we drop sequences that shouldnt progress (they return 0)
        newactive = []
        for seq in active:
            result = seq.progress(mykey)
            if result == 1:
                newactive.append(seq)
            if result == 2:
                done.append(seq)
        active = newactive

        # check if we have any keybindings that start with this key
        for binding in bindings:
            seq = binding['sequence']
            # if the key is the first in any sequence:
            newseq = KeySequence(binding['sequence'], binding['action'])
            tostart = True
            for activeseq in active:
                if activeseq.sequence == seq:
                    tostart = False
            for doneseq in done:
                if doneseq.sequence == seq:
                    tostart = False
            if tostart:
                if newseq.progress(mykey) == 1:
                    active.append(newseq)

        # clear history when no sequences are dependent on it
        # if not active:
        #     history = []

        history = history[-MAX_HIST_SIZE:]

        if not mykey.forwarded:
            towrite = False

    if towrite:
        ui.write(e.EV_KEY, code_towrite, keystate)
        ui.syn()

    return True

def myexit():
    device.ungrab()
    ui.close()
    exit(0)

def main():
    # exclusive access to device
    device.grab()

    try:
        for event in device.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                k = evdev.categorize(event)
                # print(evdev.categorize(event))
                if not handlekey(k):
                    break
    except Exception as e:
        print(e)
        myexit()
    except (KeyboardInterrupt, SystemExit, OSError) as e:
        print('exiting')
        myexit()

    print('exiting2')
    myexit()

if __name__ == '__main__':
    main()