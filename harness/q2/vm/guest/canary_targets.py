"""Development tool: measure the canary's pointer targets (runs inside the guest).

Two canary entries need screen coordinates of fixture text (``canary.yaml``
``targeting``): ``triple_click_line`` clicks the middle of the word ``this`` in
``replace this line``, and ``drag_select_word`` drags from the left edge of
``w`` to the right edge of ``d`` in ``keep word keep``. The preregistration
measures them in development and freezes them in the executor addendum
(``canary_targets.json``); this script is that measurement, never part of an
acceptance run.

* ``extents``: for Writer and Chrome, the character extents of the fixture's
  text from the accessibility tree (screen coordinates), and the targets
  derived from them: the click at the centre of the word's middle character
  boundary, the drag from one pixel inside the left edge of its first
  character to one pixel inside the right edge of its last, at the line's
  vertical centre.
* ``shot``: save a full screenshot (PIL ``ImageGrab``) to a path, for the apps
  without character extents (VS Code), measured from the image.

Usage: ``python3 -c <bootstrap> <b64> extents|shot <json>``; prints one JSON object.
"""

import json
import sys

WORDS = {
    "triple_click_line": ("replace this line", 8, 12),  # 'this'
    "drag_select_word": ("keep word keep", 5, 9),  # 'word'
}


def extents(config):
    import pyatspi

    sys.path.insert(0, config["canary_dir"])
    from canary import find_text_node  # the frozen canary driver's lookup, written there

    node = find_text_node(config["app"])
    if node is None:
        return {"ok": False, "error": "no text node"}
    if config["app"] == "writer":
        paragraphs = [node.getChildAtIndex(i) for i in range(node.childCount)]
        node = next(
            (p for p in paragraphs if p is not None and p.getRoleName() == "paragraph"), None
        )
        if node is None:
            return {"ok": False, "error": "no paragraph"}
    text = node.queryText()
    content = text.getText(0, text.characterCount)
    fixture, start, end = WORDS[config["entry"]]
    if not content.startswith(fixture):
        return {"ok": False, "error": f"unexpected text {content!r}"}
    boxes = [list(text.getCharacterExtents(i, pyatspi.DESKTOP_COORDS)) for i in range(start, end)]
    if not boxes or any(b[2] <= 0 or b[3] <= 0 for b in boxes):
        return {"ok": False, "error": "empty extents", "boxes": boxes}
    cy = boxes[0][1] + boxes[0][3] // 2
    if config["entry"] == "triple_click_line":
        middle = boxes[len(boxes) // 2]
        target = {"x": middle[0], "y": cy}
    else:
        last = boxes[-1]
        target = {
            "from": [boxes[0][0] + 1, cy],
            "to": [last[0] + last[2] - 1, cy],
            "duration_ms": 500,
        }
    return {"ok": True, "boxes": boxes, "target": target, "text": content}


def shot(config):
    from PIL import ImageGrab

    image = ImageGrab.grab()
    image.save(config["path"])
    return {"ok": True, "path": config["path"], "size": list(image.size)}


def main(argv):
    mode, config = argv[0], json.loads(argv[1])
    result = {"extents": extents, "shot": shot}[mode](config)
    result["mode"] = mode
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
