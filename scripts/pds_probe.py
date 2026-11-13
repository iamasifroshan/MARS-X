import urllib.request
import time

url = "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt00n000hb.img"
# 512 lines * 23040 bytes/line = 11,796,480 bytes (~11.25 MB)
end_byte = 512 * 23040 - 1
headers = {
    "User-Agent": "Mozilla/5.0",
    "Range": f"bytes=0-{end_byte}"
}
req = urllib.request.Request(url, headers=headers)
t0 = time.time()
with urllib.request.urlopen(req, timeout=30) as resp:
    data = resp.read()
t1 = time.time()
print(f"Downloaded {len(data)} bytes ({len(data)/(1024*1024):.2f} MB) in {t1-t0:.2f}s ({len(data)/(t1-t0)/1024/1024:.2f} MB/s)")
