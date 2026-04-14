import requests
import json
import os
from dotenv import load_dotenv
import subprocess
import sys
 
load_dotenv()

AUTH_KEY = os.getenv("API_AUTH_KEY")
headers = {"Authorization": f"Bearer {AUTH_KEY}"}
print(headers)

def cleanup_server(api_url):
    # The endpoint remains the same, but the response message is updated for clarity
    response = requests.delete(f"{api_url}/delete_data", headers=headers, timeout=None)
    if response.status_code == 200:
        data = response.json()
        # Updated to check for 'cleared_count' from our new backend logic
        print(f"Server Cleaned: {data.get('cleared_frames')} frames, {data.get("processed_frames_cleared")} processed fames and {data.get('cleared_exports')} exports removed.")
    else:
        print("Cleanup failed.")
        
def backup_to_s3(api_url):
    url = f"{api_url}/backup-data"
    print(f"[COMPILER] Requesting backup to S3/MinIO...")
    
    try:
        # stream=True is the key. 
        # timeout here applies to the 'connect' and 'first byte', 
        # but we handle the rest line-by-line.
        with requests.post(url, headers=headers, timeout=(10, None), stream=True) as response:
            if response.status_code != 200:
                print(f"[COMPILER] Backup Failed (Status {response.status_code}): {response.text}")
                return False

            for line in response.iter_lines():
                if line:
                    update = json.loads(line.decode('utf-8'))
                    status = update.get("status")
                    message = update.get("message")
                    
                    if status == "starting":
                        print(f"[COMPILER] Server: {message}")
                    elif status == "complete":
                        print(f"[COMPILER] Backup Success: {message}")
                        return True
                    elif status == "error":
                        print(f"[COMPILER] Server Error: {message}")
                        return False
            
    except requests.exceptions.Timeout:
        print(f"[COMPILER] Backup Failed: The server stopped responding during upload.")
        return False
    except Exception as e:
        print(f"[COMPILER] Connection failed: {e}")
        return False

def trigger_server_compilation(api_url, FORCE_BACKUP, DEV_MODE, filename="output"):
    # Optional: enforce .mp4
    filename = filename.split('.')[0]

    url = f"{api_url}/export-data"

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
                
                else:
                    print(data)

            except json.JSONDecodeError:
                pass

        if not final_data:
            print("[COMPILER] Error: never received completion message")
            return False

        # ----------------------------------------------------
        # FIRE BACKUP IN BACKGROUND (no progress reporting)
        # ----------------------------------------------------

        try:
            backup_params = {"filename": filename, "force_backup":FORCE_BACKUP}
            requests.post(
                f"{api_url}/backup-data",
                headers=headers,
                params=backup_params,
                timeout=1
            )
            print("[COMPILER] Backup triggered in background.")
        except Exception:
            # intentionally ignored because we don't wait for it
            print("[COMPILER] Backup trigger sent (fire-and-forget).")
        
        # try:
        #     youtube_upload_params = {"filename": filename, "dev_mode": False}
        #     requests.post(
        #         f"{api_url}/upload-data-to-yt",
        #         headers=headers,
        #         params=youtube_upload_params,
        #         timeout=1
        #     )
        #     print("[COMPILER] Youtube upload triggered in background.")
        # except Exception:
        #     # intentionally ignored because we don't wait for it
        #     print("[COMPILER] Youtube upload trigger sent (fire-and-forget).")

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

        download_urls = final_data.get("download_urls", [])
        if not download_urls:
            print("[COMPILER] No files to download.")
            return True
        
        os.makedirs(os.path.join("data", filename), exist_ok=True)
            
        for url in download_urls:
            full_url = f"{api_url.rstrip('/')}{url}"
            file_name = url.split("/")[-1]
            local_path = os.path.join("data", filename, file_name)

            try:
                with requests.get(full_url, headers=headers, stream=True) as r:
                    r.raise_for_status()
                    with open(local_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
            except Exception as e:
                print(f"Failed to download {file_name}: {e}")

        choice = input(f"\n[?] Rendering complete. Download mp4 file in background? (y/n): ").lower()
    
        if choice == 'y':
            python_exe = sys.executable
            script_path = os.path.abspath("resources/downloader.py")
            print(script_path)
            
            cmd = [
                python_exe, script_path, 
                api_url, 
                headers.get("Authorization", ""), 
                filename
            ] + ['/download/video.mp4']

            try:
                # CREATE_NEW_CONSOLE = 0x00000010
                # This is the cleanest way on Windows to launch a new terminal
                subprocess.Popen(
                    cmd, 
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                print(f"[COMPILER] Downloader launched. Check the new window.")
            except Exception as e:
                print(f"[COMPILER] Failed to launch downloader: {e}")
            
            print(f"[COMPILER] Downloader launched in a new window. You can continue working here.")
        else:
            print("[COMPILER] Download skipped by user.")

        return True

    except Exception as e:
        print(f"[COMPILER] Connection failed: {e}")
        return False
      
def ping_api(api_url):
    url = f"{api_url}/ping"
    print(f"[*] Pinging API at {url}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            server_time = data.get('server_time')
            boot_time = data.get('latest_boot')
            backup = data.get('latest_backup')

            print(f"[SUCCESS] Server is alive.")
            print(f"    - Server Time: {server_time}")
            print(f"    - Latest Boot: {boot_time}")
            
            if backup == "error":
                print("    - Latest Backup: [Error retrieving from MinIO]")
            elif backup:
                print(f"    - Latest Backup: {backup['filename']}")
                print(f"      Created: {backup['time']} ({backup['size_mb']} MB)")
            else:
                print("    - Latest Backup: None found")
                
            return True            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection failed: Is the FastAPI server running?")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    
    return False