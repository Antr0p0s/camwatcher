from dotenv import load_dotenv
import os
from resources.apiHandling import trigger_server_compilation, backup_to_s3

load_dotenv()
AUTH_KEY = os.getenv("API_AUTH_KEY")

API_URL = "https://stage.randomwebserver.eu"
DEV_MODE = False
filename = 'forced_backup'

headers = {"Authorization": f"Bearer {AUTH_KEY}"}

FORCE_BACKUP = True

success_mp4 = backup_to_s3(API_URL)
trigger_server_compilation(API_URL, True, True, [], 'triggered_backup')