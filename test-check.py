import numpy as np
path = "C:/Users/admin/OneDrive - University of Twente/stagemeasurements/chunks/05-20-10-29/chunk_1.npz"

data = np.load(path)

for key in data:
    print(f'Key: {key}, length: {len(data[key])}')