import evdev
from evdev import UInput, ecodes as e
import subprocess

from utils import *
from config import *

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
print("using device " + device.path + ' ' + device.name)

# key press history
history = []
active = []
trapped = []

def normalize(code):
    """normalize the code of a key"""
    return code.lower().replace('key_', '')

def unnormalize(code):
    if ismod(code):
        code = unmod(code)
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
                    # key.forwarded = False
                    return self.progress(key)
                return 0
            # key.forwarded = False
        elif key.code() != expected:
            # key.forwarded = False
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
            if self.action == "reload":
                print('reloading config')
                reload()
            elif isinstance(self.action, list):
                print('invoking sequence ', self.action)
                writeseq(self.action)
            else:
                self.action()
            return 2

        # return true to let this sequence continue progressing
        return 1

def writeseq(seq):
    from time import sleep
    held = []
    prev = None
    for key in seq:
        is_prev_mod = prev and ismod(prev)
        code_towrite = e.ecodes[unnormalize(key)]
        if ismod(key):
            ui.write(e.EV_KEY, code_towrite, evdev.events.KeyEvent.key_down)
            held.append(key)
            ui.syn()
        else:
            ui.write(e.EV_KEY, code_towrite, evdev.events.KeyEvent.key_down)
            ui.write(e.EV_KEY, code_towrite, evdev.events.KeyEvent.key_up)
            for heldkey in held:
                ui.write(e.EV_KEY,
                         e.ecodes[unnormalize(heldkey)],
                         evdev.events.KeyEvent.key_up)
            held = []
            ui.syn()
        rev = key
        # is this necessary to let apps process things?
        sleep(0.05)

def handlekey(key):
    """main function that handles each key event"""
    global active
    global history
    global trapped

    keystate = key.keystate
    keycode = key.keycode
    scancode = key.scancode

    # handle key remapping
    code_towrite = scancode
    for remap in remaps:
        if normalize(keycode) == remap['src']:
            code_towrite = e.ecodes[unnormalize(remap['dest'])]

    towrite = True
    was_handled = False

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
                was_handled = True
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

        if not mykey.forwarded and not was_handled:
            was_handled = False
            towrite = False
            trapped.append(mykey)

    if towrite:
        ui.write(e.EV_KEY, code_towrite, keystate)
        ui.syn()

    # if something was done, dispose the trapped sequence
    if was_handled:
        trapped = []
    # if it wasnt handled and we have no sequences that we expect will handle it,
    # we forward the entire sequence, perhaps some other app will make use of it.
    # we do this instead of disposing the sequences that arent satisfied so that
    # other apps can make use of the same patterns and modifiers (but not the
    # exact same keybindings ofc.)
    if trapped and not active:
        print('forwarding trapped sequence')
        print([key.code() for key in trapped])
        # writeseq([key.code() for key in trapped])
        trapped = []

    return True

def reload():
    import importlib
    import config
    importlib.reload(config)
    from config import bindings, remaps

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