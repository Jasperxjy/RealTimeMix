#!/usr/bin/env python3
"""Update com.realtimix.host.json with the correct Chrome extension ID.

Usage:
    python tools/generate_host_manifest.py <extension-id>

The extension ID can be found at chrome://extensions after loading the
unpacked extension in developer mode.
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_host_manifest.py <extension-id>")
        print("")
        print("Get your extension ID from chrome://extensions (Developer mode must be on).")
        sys.exit(1)

    ext_id = sys.argv[1].strip().lower()
    if len(ext_id) != 32:
        print(f"Warning: Extension ID '{ext_id}' is not 32 characters long.")
        print("Chrome extension IDs are usually 32 lowercase letters.")

    script_dir = Path(__file__).parent.resolve()
    repo_dir = script_dir.parent
    host_manifest_path = repo_dir / "native_host" / "com.realtimix.host.json"

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

    print(f"Updated {host_manifest_path}")
    print(f"Extension ID: {ext_id}")


if __name__ == "__main__":
    main()
