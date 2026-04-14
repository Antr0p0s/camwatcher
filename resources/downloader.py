# downloader.py
import requests
import sys
import os
import time

def download_files(api_url, auth_token, download_urls, folder_name):
    headers = {"Authorization": auth_token}
    os.makedirs(os.path.join("data", folder_name), exist_ok=True)
    
    print(f"--- Starting Download for {folder_name} ---")
    
    for url in download_urls:
        full_url = f"{api_url.rstrip('/')}{url}"
        file_name = url.split("/")[-1]
        local_path = os.path.join("data", folder_name, file_name)

        print(f"Downloading: {file_name}...")
        try:
            with requests.get(full_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"Saved: {file_name}")
        except Exception as e:
            print(f"Failed to download {file_name}: {e}")
            time.sleep(5)

    print("\n--- All downloads complete. This window will close in 2 seconds ---")
    time.sleep(2)

if __name__ == "__main__":
    try:
        # Check if enough arguments were passed
        if len(sys.argv) < 5:
            print("Error: Missing arguments.")
            print(f"Usage: {sys.argv[0]} <api_url> <token> <folder_name> <urls...>")
        else:
            api_url = sys.argv[1]
            token = sys.argv[2]
            folder_name = sys.argv[3]
            urls = sys.argv[4:]
            
            # Run the download logic
            # (assuming your download_files function is defined above)
            download_files(api_url, token, urls, folder_name)
            
    except Exception as e:
        print("\n--- CRITICAL ERROR ---")
        print(e)
        import traceback
        traceback.print_exc()