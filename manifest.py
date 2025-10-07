import os, json, hashlib, textwrap
root = "."  # set to your project root if needed
def sha1(p, n=1024*64):
    h = hashlib.sha1()
    with open(p,'rb') as f:
        while True:
            b=f.read(n)
            if not b: break
            h.update(b)
    return h.hexdigest()[:12]

report = {"tree":[], "files":{}}
for dp, dn, fn in os.walk(root):
    if any(s in dp for s in (".git", "__pycache__", "node_modules")): 
        continue
    for f in fn:
        p = os.path.join(dp,f)
        rel = os.path.relpath(p, root)
        report["tree"].append(rel)
        if f.endswith((".py",".html",".css",".js",".json",".md",".txt")):
            try:
                with open(p,"r",encoding="utf-8",errors="ignore") as fh:
                    lines = fh.readlines()
                report["files"][rel] = {
                    "sha": sha1(p),
                    "lines": len(lines),
                    "head": "".join(lines[:120]),
                }
            except Exception as e:
                report["files"][rel] = {"error": str(e)}
with open("kb_manifest.json","w",encoding="utf-8") as out:
    json.dump(report, out, indent=2)
print("Wrote kb_manifest.json")

