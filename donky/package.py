import json
import os
import sys
import urllib.request

def install() -> None:
    manifest_path = "donky.json"
    if not os.path.exists(manifest_path):
        print("Error: donky.json not found in current directory.")
        print("Create a donky.json file to specify dependencies.")
        sys.exit(1)
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    deps = manifest.get("dependencies", {})
    if not deps:
        print("No dependencies to install.")
        return
        
    out_dir = "donky_modules"
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Installing {len(deps)} dependencies into {out_dir}/...")
    
    for name, url in deps.items():
        filepath = os.path.join(out_dir, f"{name}.donk")
        print(f"  Downloading {name}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Donky-PM/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                code = resp.read().decode("utf-8")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            print(f"  Failed to download {name}: {e}")
            sys.exit(1)
            
    print("Done!")