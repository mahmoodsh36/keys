import subprocess
import argparse
import traceback
import evdev
from evdev import UInput, ecodes as e
from time import sleep, time

from utils import *
from config import *
from ipc import *

SYNC_DELAY = 0.03
MAX_HIST_SIZE = 150
LOG_FILE = '/tmp/keys.py.log'

keyhandler = None

def normalize(code):
    """normalize the code of a key"""
    return code.lower().replace('key_', '')

def unnormalize(code):
    if ismod(code):
        code = unmod(code)
    return f'KEY_{code.upper()}'

def is_held(keycode_normalized):
    last = last_occur(keycode_normalized)
    return last and last.is_held()

def last_occur(keycode_normalized):
    """last occurance of a key in history"""
    for histkey in reversed(keyhandler.history):
        if histkey.code() == keycode_normalized:
            return histkey

class MyKey:
    def __init__(self, keycode, scancode, keystate):
        self.keycode = keycode
        self.scancode = scancode
        self.keystate = keystate
        self.forwarded = True # whether to write it

    def is_held(self):
        return self.keystate != 'up'

    def code(self):
        original = normalize(self.keycode)
        myremap = remapped(original)
        if myremap:
            return myremap
        return original

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
                last = last_occur(unmod(expected))
                if last and last.is_held():
                    self.progress_idx += 1
                    satisfied = True
                if satisfied:
                    return self.progress(key)
                return 0
            else:
                # if the modifier key is the first key in the sequence, we choose
                # to forward and discord it to allow things like super+mouse-move
                # to work, otherwise we dont forward it
                key.forwarded = False
                if self.progress_idx == 0:
                    key.forwarded = True
                    return 0
        elif key.code() != expected:
            if self.progress_idx > 0:
                key.forwarded = False
            return 0

        seq = self.left()

        # if its not a modifier key, we check if it requires a modifier key
        # and if so we check whether that modifier key is still active (held)
        # we also need to check that no other modifier keys that arent in the
        # sequence are active
        if not ismod(expected) and self.progress_idx > 0:
            i = 1
            prev = self.sequence[self.progress_idx - i]
            if ismod(prev):
                while ismod(prev) and i <= len(self.sequence):
                    last = last_occur(unmod(prev))
                    if last and not last.is_held():
                        return 0
                    # check if a modifier key is being held when it shouldnt be
                    # this could be optimized..
                    for histkey in reversed(keyhandler.history):
                        if histkey.code() not in [unmod(other_prev) for other_prev in self.sequence[:self.progress_idx]]:
                            last = last_occur(histkey.code())
                            if last.is_held():
                                return 0
                    i += 1
                    prev = self.sequence[self.progress_idx - i]
                key.forwarded = False
            else:
                # if we have two normal keys in a row, then the second shouldnt have
                # any modifiers, here we check if any modifiers are held and if so
                # we discard this sequence
                for prev in self.sequence[:self.progress_idx]:
                    if ismod(prev):
                        last = last_occur(unmod(prev))
                        if last and last.is_held():
                            return 0
                key.forwarded = False

        self.progress_idx += 1

        # if we have reached the end of the sequence, execute the destined action
        # and return 0 to get the sequence removed.
        if self.progress_idx == len(self.sequence):
            if self.action == "reload":
                print('reloading config')
                reload()
            elif isinstance(self.action, list):
                # print('invoking sequence ', self.action)
                keyhandler.writeseq(self.action)
            else:
                self.action()
            # key.forwarded = False # we shouldnt forward key if it satisfied a keybinding
            return 2

        # return true to let this sequence continue progressing
        return 1

def all_up():
    for histkey in reversed(keyhandler.history):
        last = last_occur(histkey.code())
        if last.keystate != 'up':
            return False
    return True

def remapped(keycode_normalized):
    for remap in remaps:
        if keycode_normalized == remap['src']:
            return remap['dest']
    return None

def other_keystate_from_str(strstate):
    if strstate ==  'down':
        return evdev.events.KeyEvent.key_down
    if strstate ==  'up':
        return evdev.events.KeyEvent.key_up
    if strstate ==  'hold':
        return evdev.events.KeyEvent.key_hold

def str_keystate_from_other(keystate):
    if keystate == evdev.events.KeyEvent.key_down:
        return 'down'
    if keystate == evdev.events.KeyEvent.key_up:
        return 'up'
    if keystate == evdev.events.KeyEvent.key_hold:
        return 'hold'

def other_to_mykey(key):
    keystate = key.keystate
    keycode = key.keycode
    scancode = key.scancode
    return other_properties_to_mykey(keycode, scancode, keystate)
    # strstate = str_keystate_from_other(keystate)
    # mykey = MyKey(keycode, scancode, strstate)
    # return mykey

def other_properties_to_mykey(keycode, scancode, keystate):
    strstate = str_keystate_from_other(keystate)
    mykey = MyKey(keycode, scancode, strstate)
    return mykey

def mykey_to_other(mykey):
    keystate = other_keystate_from_str(mykey.keystate)
    keycode = key.keycode
    scancode = e.ecodes[keycode]
    return keycode, scancode, keystate

class KeyHandler:
    def __init__(self, device, ui):
        # key press history
        self.history = []
        self.active = []
        self.trapped = []
        self.after_trap = False
        self.device = device
        self.ui = ui

    def handlekey(self, mykey):
        # handle key remapping
        code_towrite = mykey.scancode
        # we sometimes get a list like ['KEY_MIN_INTERESTING', 'KEY_MUTE'] for
        # the keycode, for now we ignore those to avoid crashing
        if not isinstance(mykey.keycode, str):
            print('received unidentified/pathological key')
            return True
        for remap in remaps:
            if normalize(mykey.keycode) == remap['src']:
                code_towrite = e.ecodes[unnormalize(remap['dest'])]

        towrite = True
        was_handled = False

        # handle key up
        if mykey.keystate == 'up':
            if all_up():
                self.after_trap = False
            last = last_occur(mykey.code())
            if last:
                # if we're received "upped" keys after having releasing a trapped
                # sequence we should write those to release the keys because we dont want
                # the forwarded keys to stay "down" (for that we use after_trap).
                if not last.forwarded and not last in self.trapped and not self.after_trap:
                    towrite = False

        # handle key hold
        if mykey.keystate == 'hold':
            last = last_occur(mykey.code())
            if last:
                if not last.forwarded:
                    towrite = False

        # handle key down
        if mykey.keystate == 'down':
            # exit unconditionally
            all = "".join([histkey.code() for histkey in self.history if histkey.keystate == "down"]) + mykey.code()
            if 'force4stop' in all:
                return False # exit

            # we need to keep track of the ones we just finished to avoid
            # S-r (or the likes) from being invoked twice
            done = []

            # we drop sequences that shouldnt progress (they return 0)
            newactive = []
            for seq in self.active:
                result = seq.progress(mykey)
                if result == 1:
                    newactive.append(seq)
                if result == 2:
                    done.append(seq)
                    was_handled = True
            self.active = newactive

            # check if we have any keybindings that start with this key
            for binding in bindings:
                seq = binding['sequence']
                # if the key is the first in any sequence:
                newseq = KeySequence(binding['sequence'], binding['action'])
                tostart = True
                for activeseq in self.active:
                    if activeseq.sequence == seq:
                        tostart = False
                for doneseq in done:
                    if doneseq.sequence == seq:
                        tostart = False
                if tostart:
                    if newseq.progress(mykey) == 1:
                        self.active.append(newseq)

        self.history.append(mykey)

        if not mykey.forwarded:
            towrite = False
        if not mykey.forwarded and not was_handled:
            self.trapped.append(mykey)

        if towrite:
            self.ui.write(e.EV_KEY, code_towrite, other_keystate_from_str(mykey.keystate))
            self.ui.syn()

        # log it
        with open(LOG_FILE, "a+") as f:
            f.write(f"{time()} {mykey.keystate}({mykey.code()})\n")

        # if something was done, dispose the trapped sequence
        if was_handled:
            self.trapped = []
        # if it wasnt handled and we have no sequences that we expect will handle it,
        # we forward the entire sequence, perhaps some other app will make use of it.
        # we do this instead of disposing the sequences that arent satisfied so that
        # other apps can make use of the same patterns and modifiers (but not the
        # exact same keybindings ofc.)
        # is all_up necessary?
        if self.trapped and not self.active: # and mykey.keystate == 'up' and all_up():
            seqtowrite = []
            start_idx = len(self.history)
            for trapped_key in self.trapped:
                for i, histkey in enumerate(self.history):
                    if trapped_key == histkey:
                        if i < start_idx:
                            start_idx = i
            # print('forwarding trapped sequence')
            # print([(key.code(), key.keystate) for key in history[start_idx:]])
            self.write_raw_seq([key for key in self.history[start_idx:]])
            self.trapped = []
            self.after_trap = True

        self.history = self.history[-MAX_HIST_SIZE:]

        return True

    def handlekey_other(self, key):
        """main function that handles each key event"""
        mykey = other_to_mykey(key)
        return self.handlekey(mykey)

    def grab_device(self):
        # exclusive access to device
        self.device.grab()
        try:
            for event in self.device.read_loop():
                if event.type == evdev.ecodes.EV_KEY:
                    k = evdev.categorize(event)
                    # print(evdev.categorize(event))
                    if not self.handlekey_other(k):
                        break
        except (KeyboardInterrupt, SystemExit, OSError) as e:
            traceback.print_tb(e.__traceback__)
            print('exiting')
            myexit()
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            print(e)
            myexit()

    def writeseq(self, seq, through_handler=False):
        held = []

        # we need to syn() and wait, otherwise first key wont be invoked..
        # although this may only be needed once when the first key is to be inserted
        # if not through_handler:
        self.ui.syn()
        sleep(SYNC_DELAY)

        for key in seq:
            if ismod(key):
                code_towrite = e.ecodes[unnormalize(key)]
                if through_handler:
                    mykey = other_properties_to_mykey(unnormalize(key),
                                                      code_towrite,
                                                      evdev.events.KeyEvent.key_down)
                    self.handlekey(mykey)
                else:
                    self.ui.write(e.EV_KEY,
                                  code_towrite,
                                  evdev.events.KeyEvent.key_down)
                held.append(key)
            else:
                if 'down(' in key:
                    code = unnormalize(key[5:-1])
                    code_towrite = e.ecodes[code]
                    if through_handler:
                        mykey = other_properties_to_mykey(
                            code,
                            code_towrite,
                            evdev.events.KeyEvent.key_down)
                        self.handlekey(mykey)
                    else:
                        self.ui.write(e.EV_KEY,
                                      code_towrite,
                                      evdev.events.KeyEvent.key_down)
                elif 'up(' in key:
                    code = unnormalize(key[3:-1])
                    code_towrite = e.ecodes[code]
                    if through_handler:
                        mykey = other_properties_to_mykey(
                            code,
                            code_towrite,
                            evdev.events.KeyEvent.key_up)
                        self.handlekey(mykey)
                    else:
                        self.ui.write(e.EV_KEY,
                                      code_towrite,
                                      evdev.events.KeyEvent.key_up)
                elif 'hold(' in key:
                    code = unnormalize(key[5:-1])
                    code_towrite = e.ecodes[code]
                    if through_handler:
                        mykey = other_properties_to_mykey(
                            code,
                            code_towrite,
                            evdev.events.KeyEvent.key_hold)
                        self.handlekey(mykey)
                    else:
                        self.ui.write(e.EV_KEY,
                                      code_towrite,
                                      evdev.events.KeyEvent.key_hold)
                else:
                    code_towrite = e.ecodes[unnormalize(key)]
                    if through_handler:
                        mykey1 = other_properties_to_mykey(
                            unnormalize(key),
                            code_towrite,
                            evdev.events.KeyEvent.key_down)
                        mykey2 = other_properties_to_mykey(
                            unnormalize(key),
                            code_towrite,
                            evdev.events.KeyEvent.key_up)
                        self.handlekey(mykey1)
                        self.handlekey(mykey2)
                    else:
                        self.ui.write(e.EV_KEY,
                                      code_towrite,
                                      evdev.events.KeyEvent.key_down)
                        self.ui.write(e.EV_KEY,
                                      code_towrite,
                                      evdev.events.KeyEvent.key_up)
                for heldkey in held:
                    if through_handler:
                        mykey = other_properties_to_mykey(
                            unnormalize(heldkey),
                            e.ecodes[unnormalize(heldkey)],
                            evdev.events.KeyEvent.key_up)
                        self.handlekey(mykey)
                    else:
                        self.ui.write(e.EV_KEY,
                                      e.ecodes[unnormalize(heldkey)],
                                      evdev.events.KeyEvent.key_up)
                held = []
            # if not through_handler:
            self.ui.syn()
            # is this necessary to let apps process things?
            sleep(SYNC_DELAY)

    def write_raw_seq(self, seq, follow_rules=True):
        for key in seq:
            if key.keystate == 'down':
                event_towrite = evdev.events.KeyEvent.key_down
            if key.keystate == 'up':
                event_towrite = evdev.events.KeyEvent.key_up
            if key.keystate == 'hold':
                event_towrite = evdev.events.KeyEvent.key_hold
            code_towrite = e.ecodes[unnormalize(key.code())]
            self.ui.write(e.EV_KEY, code_towrite, event_towrite)
            self.ui.syn()
        # is this necessary to let apps process things?
        # sleep(SYNC_DELAY)

def reload():
    import importlib
    import config
    config = importlib.reload(config)
    global bindings, remaps
    bindings = config.bindings
    remaps = config.remaps

def myexit():
    if keyhandler:
        if keyhandler.device:
            keyhandler.device.ungrab()
        if keyhandler.ui:
            keyhandler.ui.close()
    exit(0)

def daemon(kbd_path=find_kbd()):
    global keyhandler
    print(f'keyboard path: {kbd_path}')
    # kbd_path = '/dev/input/event0'
    device = evdev.InputDevice(kbd_path)
    # for writing keys
    ui = UInput(name='virtual kbd')
    # our main keyhandler
    keyhandler = KeyHandler(device, ui)
    # start ipc server
    start_server(keyhandler)
    # grab device and start handling keys
    keyhandler.grab_device()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='keys.py',
        description='rebind keys',
        epilog='thank you')

    parser.add_argument('-i', '--invoke',
                        help='invoke the given key sequence')
    parser.add_argument('-th', '--through_handler',
                        action='store_true',
                        help="""to be used with --invoke, to invoke the keys through
                        the handler, so that special keybindings may be handled
                        properly""")
    parser.add_argument('-td', '--through_daemon',
                        action='store_true',
                        help="""to be used with --invoke, to send the keys to the
                        daemon for it to invoke.""")
    parser.add_argument('-k', '--sendkeys',
                        help='send keys to be handled by the main daemon')
    parser.add_argument('-d', '--daemon',
                        action='store_true',
                        help='start the key daemon (which grabs the kbd device)')
    parser.add_argument('-m', '--monitor',
                        action='store_true',
                        help='monitor keyboard events')
    parser.add_argument('-pk', '--print_kbd',
                        action='store_true',
                        help='show keyboard device location under /dev/input')
    parser.add_argument('-s', '--send',
                        help="send a message to the daemon")
    parser.add_argument('-p', '--kbd-path',
                        help="specify the path to the keyboard that should be captured")

    args = parser.parse_args()

    if args.invoke:
        keyhandler = KeyHandler(None, UInput(name='virtual kbd'))
        if args.through_daemon:
            client('writeseq ' + args.invoke)
        else:
            if args.through_handler:
                keyhandler.writeseq(eval(args.invoke), through_handler=True)
            else:
                keyhandler.writeseq(eval(args.invoke))

    if args.send:
        client(args.send)

    if args.print_kbd:
        print(find_kbd())

    if args.daemon:
        print('starting daemon')
        if args.kbd_path:
            daemon(args.kbd_path)
        else:
            daemon()

    if args.monitor:
        print('monitoring')

    if args.sendkeys:
        # keyhandler = KeyHandler(None, UInput(name='virtual kbd'))
        # keyhandler.writeseq(eval(args.invoke))
        if args.through_handler:
            pass

    myexit()