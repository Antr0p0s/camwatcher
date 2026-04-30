import math

OFFSETS = [0, -24.501, -42.082, -16.723] # blue, black, red, white
COEFFICIENTS = [0, 2.108, 2.8839, 1.6371]

def convert_temperature(measured_temp, probe_no):
    if probe_no ==  0: # blue
        return 0.00052213 * math.exp(0.52389 * measured_temp)
    return COEFFICIENTS[probe_no] * measured_temp + OFFSETS[probe_no]