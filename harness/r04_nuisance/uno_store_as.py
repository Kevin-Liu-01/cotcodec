"""Save As in the document's own format through the running GUI instance (UNO client).

Run by the save stage with the build's own Python and pyuno (the VM's Python with Ubuntu's
python3-uno for the VM's build; the bundled ``program/python`` of a TDF build). It
connects to the instance's UNO pipe, finds the open document whose file is ``--path``,
reads the filter the document was loaded with (``getArgs()`` ``FilterName``) and calls
``storeAsURL`` on the document's own URL with that filter and ``Overwrite``: what File >
Save As > same name > same format does, without the dialog. Prints one JSON line.

Standard library plus ``uno`` only, and no syntax newer than Python 3.8.
"""

import argparse
import json
import os
import sys
import time


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pipe", required=True)
    parser.add_argument("--path", required=True, help="the document's file system path")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    out = {"ok": False, "filter": None, "error": None, "matched_url": None}
    try:
        import uno
        from com.sun.star.beans import PropertyValue

        def prop(name, value):
            item = PropertyValue()
            item.Name = name
            item.Value = value
            return item

        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local
        )
        deadline = time.time() + args.timeout
        ctx = None
        while ctx is None:
            try:
                ctx = resolver.resolve(f"uno:pipe,name={args.pipe};urp;StarOffice.ComponentContext")
            except Exception as exc:  # noqa: BLE001 - retried until the deadline
                if time.time() > deadline:
                    raise RuntimeError(f"no UNO connection: {exc}") from exc
                time.sleep(0.25)
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = None
        while doc is None:
            components = desktop.getComponents().createEnumeration()
            while components.hasMoreElements():
                comp = components.nextElement()
                url = comp.getURL() if hasattr(comp, "getURL") else ""
                if url.startswith("file:") and os.path.normpath(
                    uno.fileUrlToSystemPath(url)
                ) == os.path.normpath(args.path):
                    doc = comp
                    break
            if doc is None:
                if time.time() > deadline:
                    raise RuntimeError(f"document not open: {args.path}")
                time.sleep(0.25)
        url = doc.getURL()
        out["matched_url"] = url
        filter_name = None
        for item in doc.getArgs():
            if item.Name == "FilterName":
                filter_name = item.Value
        if not filter_name:
            raise RuntimeError("document has no load filter")
        out["filter"] = filter_name
        doc.storeAsURL(url, (prop("FilterName", filter_name), prop("Overwrite", True)))
        out["ok"] = True
    except BaseException as exc:  # noqa: BLE001 - reported to the save stage
        out["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    sys.stdout.write(json.dumps(out, sort_keys=True) + "\n")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
