"""Fetch run 1's job.py from the published repository into this folder.

The follow-up reuses run 1's code unchanged, so it runs against exactly what is
public. Apache-2.0. Standard library only.
"""
import os
import urllib.request

URLS = [
    "https://raw.githubusercontent.com/munimtechnologies/w3c-spec-lifecycle/main/job.py",
    "https://github.com/munimtechnologies/w3c-spec-lifecycle/raw/main/job.py",
]
HERE = os.path.dirname(os.path.abspath(__file__))

for url in URLS:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mv2-munim-research/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
    except OSError as exc:
        print("failed %s: %r" % (url, exc))
        continue
    if b"def core_metrics" in body:
        with open(os.path.join(HERE, "job.py"), "wb") as fh:
            fh.write(body)
        print("fetched job.py (%d bytes) from %s" % (len(body), url))
        break
else:
    raise SystemExit("could not fetch job.py")
