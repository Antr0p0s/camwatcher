import requests
import os
from dotenv import load_dotenv
from resources.apiHandling import trigger_server_compilation, cleanup_server

load_dotenv()

# Ensure this matches your FastAPI server port
API_URL = "https://stage.randomwebserver.eu"
API_URL = 'http://127.0.0.1:8000' 
AUTH_KEY = os.getenv("API_AUTH_KEY")

# Added User-Agent to help bypass proxy redirects (like the /lander issue)
headers = {
    "Authorization": f"Bearer {AUTH_KEY}",
}

def get_backups():
    print("[*] Fetching backups from MinIO...")
    try:
        response = requests.get(f"{API_URL}/list-backups", headers=headers)
        if response.status_code == 200:
            backups = response.json().get("backups", [])
            
            # --- SORTING LOGIC ---
            # Server sends Newest -> Oldest. 
            # We reverse it to get Oldest -> Newest (Newest at Bottom).
            backups.reverse() 
            return backups
        else:
            print(f"[!] Failed to fetch ({response.status_code}): {response.text}")
            return []
    except Exception as e:
        print(f"[!] Connection Error: {e}")
        return []

def trigger_compilation(backup_key):
    # STEP 1: RESTORE DATA TO RAM
    # We must restore the backup into the server's memory before compiling
    print(f"\n[1/2] Restoring {backup_key} to server RAM...")
    try:
        restore_res = requests.post(
            f"{API_URL}/restore-backup", 
            params={"backup_key": backup_key}, 
            headers=headers
        )
        if restore_res.status_code != 200:
            print(f"[!] Restore failed: {restore_res.text}")
            return
    except Exception as e:
        print(f"[!] Restore connection error: {e}")
        return

    # STEP 2: COMPILE VIDEO
    
    print(f"[2/2] Compiling results for backup: {backup_key}")
    trigger_server_compilation(API_URL, False, 'restored_backup')

def main_menu():
    backups = get_backups()
    
    if not backups:
        print("No backups found.")
        return

    print("\n=== AVAILABLE BACKUPS (Newest at Bottom) ===")
    for i, b in enumerate(backups):
        time_str = b['last_modified'].replace("T", " ")[:19]
        print(f"[{i}] {time_str} | {b['size_mb']} MB | {b['key']}")

    print(f"[x] Cancel")

    try:
        user_input = input("\nSelect a backup number to compile: ")
        if user_input.lower() == 'q' or user_input.lower() == 'x':
            print("Operation cancelled.")
            return
        
        choice = int(user_input)
        selected_backup = backups[choice]['key']
        
        trigger_compilation(selected_backup)
            
    except (ValueError, IndexError):
        print("Invalid selection.")

if __name__ == "__main__":
    main_menu()