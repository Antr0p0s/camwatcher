import requests
from dotenv import load_dotenv
import os
from resources.apiHandling import cleanup_server
import json

load_dotenv()
AUTH_KEY = os.getenv("API_AUTH_KEY")

headers = {"Authorization": f"Bearer {AUTH_KEY}"}

DEV_MODE = False
API_URL = 'http://127.0.0.1:8000/' if DEV_MODE else "https://stage.randomwebserver.eu"

cleanup_server(API_URL)

keys1 = [f"1stage/2026-04-07/crystallise_/data.npz",f"1stage/2026-04-07/crystallise_/data.npz"]
keys2 = [f"1stage/2026-04-07/crystallise_15_1/data.npz",f"1stage/2026-04-07/crystallise_15_1_pt2/data.npz"]

keys = keys1 if DEV_MODE else keys2
response = requests.post(
    f"{API_URL}/restore-backup-array", 
    json=keys,
    headers=headers
)
print(response.json())

def trigger_server_merging(api_url, FORCE_BACKUP = False, filename="merged_backup"):
    # Optional: enforce .mp4
    filename = filename.split('.')[0]

    url = f"{api_url}/export-merged-data"

    print(f"[COMPILER] Requesting export with limits")

    try:
        response = requests.post(
            url,
            headers=headers,
            stream=True,
            timeout=None
        )

        if response.status_code != 200:
            print(f"[COMPILER] Server Error: {response.status_code} - {response.text}")
            return False

        final_data = None

        for line in response.iter_lines():

            if not line:
                continue

            decoded_line = line.decode("utf-8").strip()

            try:
                data = json.loads(decoded_line)
                
                if data.get("status") == "processing":
                    print(f"[SERVER] {data.get('message')}")

                elif data.get("status") == "complete":
                    final_data = data
                    print(f"[COMPILER] Export complete! Total frames: {data.get('total_frames')}")

                elif data.get("status") == "error":
                    print(f"[COMPILER] Server-side error: {data['message']}")
                    return False

            except json.JSONDecodeError:
                pass

        if not final_data:
            print("[COMPILER] Error: never received completion message")
            return False

        # ----------------------------------------------------
        # DOWNLOAD VIDEO
        # ----------------------------------------------------
        if not final_data:
            print("[COMPILER] No final data received.")
            return False

        os.makedirs("data", exist_ok=True)

        # --- NEW: handle multiple files ---
        download_urls = final_data.get("download_urls")

        # Backward compatibility (if server still sends single file)
        if not download_urls and "download_url" in final_data:
            download_urls = [final_data["download_url"]]

        if not download_urls:
            print("[COMPILER] No download URLs returned.")
            return False

        print(f"[COMPILER] Downloading {len(download_urls)} file(s)...")

        for url in download_urls:
            full_url = f"{api_url.rstrip('/')}{url}"
            
            # Extract filename from URL
            file_name = url.split("/")[-1]
            local_path = os.path.join("data", filename, file_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            with requests.get(full_url, headers=headers, stream=True) as r:
                r.raise_for_status()

                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            print(f"[COMPILER] Saved → {filename}/{file_name} to disk")

        print("[COMPILER] All downloads complete.")

        return True

    except Exception as e:
        print(f"[COMPILER] Connection failed: {e}")
        return False
    
trigger_server_merging(API_URL)
cleanup_server(API_URL)
