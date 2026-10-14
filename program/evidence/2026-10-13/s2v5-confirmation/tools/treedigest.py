"""Digest of an exported tree: sorted '<relpath>\0<sha256 or ->target>\n' lines (.git_sha excluded).

Prints JSON: files, symlinks, tree digest, and the per-subtree digests of harness/ and infra/.
Standard library only; reads the tree, writes nothing.
"""
import hashlib, json, os, sys

def walk(root, sub=""):
    base = os.path.join(root, sub) if sub else root
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames.sort()
        for name in dirnames + filenames:
            p = os.path.join(dirpath, name)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if rel == ".git_sha":
                continue
            if os.path.islink(p):
                out.append((rel, "->" + os.readlink(p)))
            elif os.path.isfile(p) and name in filenames:
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                out.append((rel, h.hexdigest()))
    out.sort()
    return out

def digest(entries):
    o = hashlib.sha256()
    for rel, d in entries:
        o.update(f"{rel}\0{d}\n".encode())
    return o.hexdigest()

root = sys.argv[1]
allx = walk(root)
res = {"files": sum(1 for _, d in allx if not d.startswith("->")),
       "symlinks": sum(1 for _, d in allx if d.startswith("->")),
       "tree": digest(allx)}
for sub in ("harness", "infra", "experiments", "tests", "program"):
    res[sub] = digest([e for e in allx if e[0].startswith(sub + "/")])
if len(sys.argv) > 2:
    with open(sys.argv[2], "w") as f:
        for rel, d in allx:
            f.write(f"{d}  {rel}\n")
print(json.dumps(res, sort_keys=True))
