import numpy as np
import requests
import io
import os

url = "http://127.0.0.1:8000/upload_file"
file_path = "chunks/chunk_0006.npy"

AUTH_KEY = "0rwWNngAeS5lBaGURxLDFHdX9J71YOzykMPoE4KCi38smI6ucbVtTpqZhvf2jQ"
headers = {"Authorization": f"Bearer {AUTH_KEY}"}

# 1. Read the numpy file into an object (array)
# This is the "object" you'll be working with in the future
data_object = np.load(file_path)

# 2. Convert that object into a byte stream
buffer = io.BytesIO()
np.save(buffer, data_object)
buffer.seek(0) # Reset buffer pointer to the beginning

# 3. Send the stream as a file to the API
# We use the original filename so the server knows what it's getting
files = {
    "file": (os.path.basename(file_path), buffer, "application/octet-stream")
}

print(f"Uploading {os.path.basename(file_path)} as an object...")
response = requests.post(url, files=files, timeout=None, headers=headers)

print(response.json())