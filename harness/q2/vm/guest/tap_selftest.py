"""Oracle self-test for the XRecord tap (runs inside the OSWorld guest).

Infrastructure validation of the oracle, not a trial of any system under test:
it checks that the tap reports the keysym in force when a key event happens,
including after the keyboard mapping changes. One spare keycode (no keysyms
at any level) is remapped with core ``ChangeKeyboardMapping`` three times
(``eacute``, then U+0416 as a Unicode keysym, then back to NoSymbol), and after
each change it is pressed and released once with XTest. The tap must report
the three keysyms in that order on that keycode. With the previous tap, which
read keysyms from a cache filled when it connected, all six events would have
been reported as 0x0.

Prints one JSON object: the keycode, the expected (kind, keycode, keysym0)
sequence and the original row of the keycode (restored at the end).
"""

import json
import time

from Xlib import X, display
from Xlib.ext import xtest

SEQUENCE = [0x00E9, 0x01000416, 0]  # eacute, U+0416 CYRILLIC CAPITAL LETTER ZHE, NoSymbol


def main():
    d = display.Display()
    info = d.display.info
    first, last = info.min_keycode, info.max_keycode
    rows = d.get_keyboard_mapping(first, last - first + 1)
    spare = [first + i for i, row in enumerate(rows) if not any(row)]
    if not spare:
        print(json.dumps({"error": "no spare keycode"}))
        return
    keycode = spare[-1]
    original = list(rows[keycode - first])
    expected = []
    try:
        for keysym in SEQUENCE:
            d.change_keyboard_mapping(keycode, [[keysym] * len(original)])
            d.sync()
            time.sleep(0.2)
            xtest.fake_input(d, X.KeyPress, keycode)
            xtest.fake_input(d, X.KeyRelease, keycode)
            d.sync()
            time.sleep(0.2)
            expected += [["KeyPress", keycode, keysym], ["KeyRelease", keycode, keysym]]
    finally:
        d.change_keyboard_mapping(keycode, [original])
        d.sync()
    print(json.dumps({"keycode": keycode, "expected": expected, "original_row": original}))


if __name__ == "__main__":
    main()
