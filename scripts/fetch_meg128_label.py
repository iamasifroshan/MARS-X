import os
import urllib.request
import hashlib
import time

url_lbl = "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt00n000hb.lbl"
out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "mola"))
os.makedirs(out_dir, exist_ok=True)
lbl_path = os.path.join(out_dir, "megt00n000hb.lbl")

headers = {"User-Agent": "MARS-X-PDS/1.0 (NASA Space Apps 2026)"}
req = urllib.request.Request(url_lbl, headers=headers)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = resp.read()
    with open(lbl_path, "wb") as f:
        f.write(data)

sha = hashlib.sha256(data).hexdigest()
print(f"Downloaded megt00n000hb.lbl ({len(data)} bytes, SHA-256: {sha})")
