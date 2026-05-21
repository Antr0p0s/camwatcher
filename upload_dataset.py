import numpy as np
import os
from resources.apiHandling import cleanup_server, ping_api, trigger_server_compilation, backup_to_s3
import requests
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv()

AUTH_KEY = os.getenv("API_AUTH_KEY")

headers = {
    "Authorization": f"Bearer {AUTH_KEY}"
}

def upload_single_chunk(
    api_url,
    chunk_path,
    chunk_index,
    timeout=120
):
    """
    Upload a single .npz chunk file to the API.
    """

    if not os.path.exists(chunk_path):
        raise FileNotFoundError(chunk_path)

    with open(chunk_path, "rb") as f:
        files = {
            "file": (
                os.path.basename(chunk_path),
                f,
                "application/octet-stream"
            )
        }

        response = requests.post(
            f"{api_url}/upload_data",
            files=files,
            headers=headers,
            data={
                "chunk_index": chunk_index
            },
            timeout=timeout
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Upload failed: "
            f"{response.status_code} - "
            f"{response.text}"
        )

    return response.json()


API_URL = "https://stage-api.randomwebserver.eu"
# API_URL = "http://127.0.0.1:8000"

if not ping_api(API_URL):
    raise LookupError('Server not online')

path = "D:/Jelmer/Documents/University of Twente/OneDrive - University of Twente/stagemeasurements/chunks/raw - procent 263"
index = 1
# 4 moet video nog maar die is raar aan t doen

files = os.listdir(f'{path} - {index}')
filename = f'{path.split('/')[-1]} - {index}'

SAVE_DATA = False

if SAVE_DATA:
    backup_to_s3(API_URL, filename)
else:
    print(f'Need to upload {len(files)} files')
    startindex = 2
    if startindex == 1:
        cleanup_server(API_URL)

    for i in range(startindex, len(files)):
        full_path = f'{path} - {index}/chunk_{i}.npz'
        print(f'uploading {full_path} ({i}/{len(files)})')

        result = upload_single_chunk(
            api_url=f'{API_URL}',
            chunk_path=full_path,
            chunk_index=i - 1
        )
        print(result)
        time.sleep(5)
        i+=1

    time.sleep(1)
    print('triggering upload')
    trigger_server_compilation(API_URL, True, False, [0], filename)
    time.sleep(1)
    print('compiling video done')
