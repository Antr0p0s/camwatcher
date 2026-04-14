import requests
import os
from dotenv import load_dotenv
import subprocess
import sys

load_dotenv()

AUTH_KEY = os.getenv("API_AUTH_KEY")
headers = {"Authorization": f"Bearer {AUTH_KEY}"}

# Ensure this matches your FastAPI server port
API_URL = "https://stage.randomwebserver.eu"
# API_URL = 'http://127.0.0.1:8000/'

def trigger_latest_download(api_url, filename="output"):
    url = f"{api_url}/get_generated_files"
    
    print(f'Getting latest files from {url}')
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            download_urls = data.get('download_urls')
            python_exe = sys.executable
            script_path = os.path.abspath("resources/downloader.py")
            
            cmd = [
                python_exe, script_path, 
                api_url, 
                headers.get("Authorization", ""), 
                filename
            ] + download_urls

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
                
            return True     
        else:
            print(response)       
        
    except Exception as e:
        print(f"[COMPILER] Connection failed: {e}")
        return False

trigger_latest_download(API_URL)