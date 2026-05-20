import numpy as np
path = ''

data = np.load(path)

for key in data:
    print(f'Key: {key}, length: {len(data[key])}')