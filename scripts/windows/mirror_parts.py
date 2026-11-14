"""(LaküenRecomp) The parts scripts/windows/mirror_parts.txt names that the builder-parts release lacks, downloaded (or, for the
play profile, made by profile_part.py) and checked against their SHA-256 and size, into a folder for the workflow to upload.

    python -I scripts/windows/mirror_parts.py <out folder> [--have <file of the release's asset names, one a line>]
"""
import argparse
import hashlib
import os
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import profile_part  # noqa: E402


def entries(path=os.path.join(HERE, "mirror_parts.txt")):
    """(name, sha256, size, source) of each part, in the file's order"""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            w = line.split()
            if w and not w[0].startswith("#"):
                out.append((w[0], w[1], int(w[2]), w[3]))
    return out


def get(url, dest, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lakuen-mirror"}), timeout=300) as r, \
                    open(dest, "wb") as f:
                while b := r.read(1 << 20):
                    f.write(b)
            return
        except OSError as e:   # (GitHub answers 502/504 now and then)
            if i == tries - 1:
                raise
            print("%s: %s, again" % (url, e), file=sys.stderr)
            time.sleep(5 * (i + 1))


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


def fetch(name, sha, size, source, out):
    dest = os.path.join(out, name)
    if source.startswith("profile:"):
        url, src_sha = source[len("profile:"):].rsplit(":", 1)
        with tempfile.TemporaryDirectory() as d:
            share = os.path.join(d, "share.zip")
            get(url, share)
            if digest(share) != src_sha:
                sys.exit("%s: not the SHA-256 mirror_parts.txt gives" % url)
            profile_part.main(share, dest)
    else:
        get(source, dest)
    if os.path.getsize(dest) != size or digest(dest) != sha:
        os.remove(dest)
        sys.exit("%s: not the size and SHA-256 mirror_parts.txt gives" % name)
    print("%s: ready (%d MB)" % (name, size >> 20))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("out")
    p.add_argument("--have")
    a = p.parse_args(argv)
    have = set()
    if a.have:
        with open(a.have, encoding="utf-8") as f:
            have = {l.strip() for l in f if l.strip()}
    os.makedirs(a.out, exist_ok=True)
    for name, sha, size, source in entries():
        if name in have:
            print("%s: already there" % name)
        else:
            fetch(name, sha, size, source, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
