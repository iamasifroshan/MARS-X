import json
import os
import hashlib

with open("docs/research/dataset_provenance_registry.json", "r", encoding="utf-8") as f:
    registry = json.load(f)

print(f"Registry: {registry.get('registry_version')} (Total datasets: {len(registry.get('datasets', []))})\n")

for d in registry.get("datasets", []):
    ds_id = d.get("dataset_id")
    status = d.get("production_status")
    local_files = d.get("local_files")
    official_urls = d.get("official_urls")
    print(f"Dataset: {ds_id} (Status: {status})")
    if isinstance(local_files, dict):
        for k, p in local_files.items():
            exists = os.path.exists(p)
            size = os.path.getsize(p) if exists else 0
            url = official_urls.get(k) if isinstance(official_urls, dict) else ""
            print(f"  [{k}] path='{p}' exists={exists} size={size:,} bytes")
            if url:
                print(f"       url={url}")
    elif isinstance(local_files, str):
        exists = os.path.exists(local_files)
        size = os.path.getsize(local_files) if exists else 0
        print(f"  path='{local_files}' exists={exists} size={size:,} bytes")
    print()
