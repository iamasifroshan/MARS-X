import os
import sys
import time
import urllib.request
import hashlib

url = "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt00n000hb.img"
out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "mola"))
out_file = os.path.join(out_dir, "megt00n000hb.img")

print(f"Starting download of MOLA 128 px/deg tile (MEGT00N000HB.IMG, ~124 MB)...")
headers = {"User-Agent": "MARS-X-PDS/1.0 (NASA Space Apps 2026)"}
req = urllib.request.Request(url, headers=headers)

t0 = time.time()
sha = hashlib.sha256()
downloaded = 0
total_size = 129761280

with urllib.request.urlopen(req, timeout=120) as resp:
    with open(out_file, "wb") as f:
        while True:
            chunk = resp.read(1024 * 512)
            if not chunk:
                break
            f.write(chunk)
            sha.update(chunk)
            downloaded += len(chunk)
            elapsed = time.time() - t0
            speed = downloaded / (elapsed + 0.001) / 1024 / 1024
            pct = (downloaded / total_size) * 100
            sys.stdout.write(f"\rDownloaded {downloaded:,} / {total_size:,} bytes ({pct:.1f}%) @ {speed:.2f} MB/s")
            sys.stdout.flush()

t1 = time.time()
print(f"\nDownload completed in {t1 - t0:.1f}s. SHA-256: {sha.hexdigest()}")
