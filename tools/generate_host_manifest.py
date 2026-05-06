#!/usr/bin/env python3
"""Generate com.realtimix.host.json with the correct allowed_origins.

If browser_extension/manifest.json contains a 'key' field, this script extracts
the corresponding Chrome extension ID and writes it into the host manifest.
Otherwise it computes the ID from the extension directory path (unpacked).
"""
import json
import base64
import hashlib
import sys
from pathlib import Path


def compute_extension_id_from_key(key_b64: str) -> str:
    """Chrome extension ID = first 16 bytes of SHA256(pubkey DER) as lowercase hex."""
    pubkey_der = base64.b64decode(key_b64)
    return hashlib.sha256(pubkey_der).hexdigest()[:32]


def compute_extension_id_from_path(ext_dir: Path) -> str:
    """Compute unpacked extension ID from absolute directory path.
    
    Chrome uses the first 128 bits of SHA256(dir_path) as the extension ID.
    The path must be absolute and use the same canonical casing as on disk.
    """
    abs_path = str(ext_dir.resolve())
    return hashlib.sha256(abs_path.encode("utf-8")).hexdigest()[:32]


def main():
    script_dir = Path(__file__).parent.resolve()
    repo_dir = script_dir.parent
    ext_dir = repo_dir / "browser_extension"
    manifest_path = ext_dir / "manifest.json"
    host_manifest_path = repo_dir / "native_host" / "com.realtimix.host.json"

    if not manifest_path.exists():
        print(f"ERROR: Extension manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    key = manifest.get("key")
    if key:
        ext_id = compute_extension_id_from_key(key)
        print(f"Extension ID from manifest key: {ext_id}")
    else:
        ext_id = compute_extension_id_from_path(ext_dir)
        print(f"Extension ID from directory path: {ext_id}")

    if host_manifest_path.exists():
        with open(host_manifest_path, "r", encoding="utf-8-sig") as f:
            host_manifest = json.load(f)
    else:
        host_manifest = {
            "name": "com.realtimix.host",
            "description": "RealTimeMix Native Messaging Host",
            "path": str(repo_dir / "native_host" / "host.bat"),
            "type": "stdio",
            "allowed_origins": [],
        }

    host_manifest["allowed_origins"] = [f"chrome-extension://{ext_id}/"]

    with open(host_manifest_path, "w", encoding="utf-8") as f:
        json.dump(host_manifest, f, ensure_ascii=False, indent=4)

    print(f"Updated: {host_manifest_path}")


if __name__ == "__main__":
    main()
