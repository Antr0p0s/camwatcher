import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = "https://stage.randomwebserver.eu"
# API_URL = 'http://127.0.0.1:8000/'

AUTH_KEY = os.getenv("API_AUTH_KEY")
headers = {"Authorization": f"Bearer {AUTH_KEY}"}

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

# Run it
ping_api(API_URL) 