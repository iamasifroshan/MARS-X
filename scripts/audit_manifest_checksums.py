import os
import json
import hashlib

def sha256_file(filepath):
    if not os.path.isfile(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

with open('docs/research/dataset_provenance_registry.json', 'r', encoding='utf-8') as f:
    reg = json.load(f)

print(f"Total datasets in registry: {len(reg.get('datasets', []))}\n")
for d in reg.get('datasets', []):
    ds_id = d.get('dataset_id')
    title = d.get('title')
    cat = d.get('category')
    tier = d.get('resolution_tier')
    print(f"=== {ds_id} ({cat} | {tier}) ===")
    files = d.get('local_files', {})
    if isinstance(files, str):
        files = {'default': files}
    urls = d.get('official_urls', {})
    if isinstance(urls, str):
        urls = {'default': urls}
    csums = d.get('checksums', {})
    for k, p in files.items():
        exists = os.path.exists(p)
        sz = os.path.getsize(p) if exists else 0
        expected_sha = csums.get(k, '')
        actual_sha = sha256_file(p) if exists and sz < 300 * 1024 * 1024 else ('skipped_too_large' if exists else 'missing')
        url = urls.get(k, 'N/A')
        print(f"  [{k}] path={p} exists={exists} size={sz:,} bytes")
        print(f"       expected_sha={expected_sha}")
        print(f"       actual_sha  ={actual_sha}")
        print(f"       match={(expected_sha == actual_sha) if expected_sha and actual_sha not in ('missing', 'skipped_too_large') else 'N/A'}")
        print(f"       url={url}")
    print()
